from flask import Blueprint, jsonify, request
import subprocess
import re
from database import get_db, install_store_app, uninstall_store_app

store_bp = Blueprint("store", __name__)

APPSTORE_URL = "https://raw.githubusercontent.com/mustafacil38/armpanel/main/appstore.txt"


KNOWN_KEYS = {
    "name", "icon", "description", "default_port", "config_files",
    "process_name", "command_start", "command_stop", "command_restart",
    "install_script", "uninstall_script"
}

def _parse_appstore(text):
    apps = []
    blocks = text.split("=== APP ===")
    for block in blocks:
        block = block.strip()
        if not block or block.startswith("=== END ==="):
            continue
        end_idx = block.find("=== END ===")
        if end_idx != -1:
            block = block[:end_idx]
        app = {}
        last_key = None
        for line in block.strip().splitlines():
            s = line.strip().replace('\r', '')
            if not s:
                continue
            
            is_known_key = False
            if "=" in s:
                key_candidate, _, val_candidate = s.partition("=")
                key_candidate = key_candidate.strip()
                if key_candidate in KNOWN_KEYS:
                    value = val_candidate.strip()
                    if key_candidate == "default_port":
                        try:
                            value = int(value)
                        except ValueError:
                            value = 0
                    app[key_candidate] = value
                    last_key = key_candidate
                    is_known_key = True
            
            if not is_known_key and last_key in ("install_script", "uninstall_script"):
                app[last_key] = app.get(last_key, "") + "\n" + s
                
        if app.get("name"):
            apps.append(app)
    return apps


def _load_local_appstore():
    import os
    local_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'appstore.txt'))
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def _fetch_appstore():
    import urllib.request
    data = None
    try:
        with urllib.request.urlopen(APPSTORE_URL, timeout=10) as resp:
            data = resp.read().decode("utf-8")
    except Exception:
        data = None
    if not data:
        data = _load_local_appstore()
    return data


def _get_installed_names():
    conn = get_db()
    rows = conn.execute("SELECT name FROM services").fetchall()
    conn.close()
    return {r["name"] for r in rows}


@store_bp.route("/api/store")
def store_list():
    text = _fetch_appstore()
    if text is None:
        return jsonify({"ok": False, "error": "AppStore yüklenemedi"}), 502

    apps = _parse_appstore(text)
    installed = _get_installed_names()

    for app in apps:
        app["installed"] = app["name"] in installed

    return jsonify({"ok": True, "apps": apps})


@store_bp.route("/api/store/install", methods=["POST"])
def store_install():
    data = request.get_json()
    app_name = data.get("name", "")

    text = _fetch_appstore()
    if text is None:
        return jsonify({"ok": False, "error": "AppStore yüklenemedi"}), 502

    apps = _parse_appstore(text)
    target = None
    for app in apps:
        if app["name"] == app_name:
            target = app
            break

    if not target:
        return jsonify({"ok": False, "error": "Uygulama bulunamadı"}), 404

    script = target.get("install_script", "")
    if not script:
        return jsonify({"ok": False, "error": "Kurulum scripti boş"}), 400

    try:
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True, text=True, timeout=600
        )
        if result.stdout:
            print("[STORE_INSTALL][STDOUT]", result.stdout)
        if result.stderr:
            print("[STORE_INSTALL][STDERR]", result.stderr)
        
        if result.returncode != 0:
            return jsonify({
                "ok": False,
                "error": f"Kurulum başarısız (kod {result.returncode}): {result.stderr[-500:]}"
            }), 500

        install_store_app(target)

        success_msg = f"{app_name} kuruldu"
        if result.stderr:
            success_msg += f"\n\nNot: {result.stderr[:200]}"
        return jsonify({"ok": True, "message": success_msg})
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "Kurulum zaman aşımı"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@store_bp.route("/api/store/uninstall", methods=["POST"])
def store_uninstall():
    data = request.get_json()
    app_name = data.get("name", "")

    conn = get_db()
    row = conn.execute("SELECT id FROM services WHERE name = ?", (app_name,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Uygulama bulunamadı"}), 404

    text = _fetch_appstore()
    script = ""
    if text:
        apps = _parse_appstore(text)
        for app in apps:
            if app["name"] == app_name:
                script = app.get("uninstall_script", "")
                break

    if script:
        try:
            subprocess.run(
                ["bash", "-c", script],
                capture_output=True, text=True, timeout=300
            )
        except Exception:
            pass

    uninstall_store_app(app_name)
    conn.close()

    return jsonify({"ok": True, "message": f"{app_name} kaldırıldı"})

import os
import subprocess
import shutil
import psutil
from flask import Blueprint, request, jsonify
from database import get_db

services_bp = Blueprint("services", __name__)

ALLOWED_CONFIG_DIRS = ["/etc/nginx", "/etc/php", "/etc/filebrowser", "/etc/ttyd", "/usr/local/etc"]


def _is_config_allowed(path):
    path = os.path.realpath(path)
    for d in ALLOWED_CONFIG_DIRS:
        if path.startswith(d):
            return True
    return False


def _is_running(process_name):
    if not process_name:
        return False
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            name = proc.info.get("name", "")
            cmdline = " ".join(proc.info.get("cmdline", []) or [])
            if process_name.lower() in name.lower() or process_name.lower() in cmdline.lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


@services_bp.route("/api/services", methods=["GET"])
def list_services():
    conn = get_db()
    rows = conn.execute("SELECT * FROM services ORDER BY id").fetchall()
    conn.close()

    services = []
    for row in rows:
        svc = dict(row)
        svc["is_running"] = _is_running(svc["process_name"])
        services.append(svc)
    return jsonify(services)


@services_bp.route("/api/services/<int:sid>/start", methods=["POST"])
def start_service(sid):
    conn = get_db()
    svc = conn.execute("SELECT * FROM services WHERE id = ?", (sid,)).fetchone()
    conn.close()
    if not svc:
        return jsonify({"ok": False, "error": "Service not found"}), 404

    try:
        subprocess.Popen(svc["command_start"], shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify({"ok": True, "message": f"{svc['name']} başlatılıyor..."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@services_bp.route("/api/services/<int:sid>/stop", methods=["POST"])
def stop_service(sid):
    conn = get_db()
    svc = conn.execute("SELECT * FROM services WHERE id = ?", (sid,)).fetchone()
    conn.close()
    if not svc:
        return jsonify({"ok": False, "error": "Service not found"}), 404

    try:
        subprocess.Popen(svc["command_stop"], shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify({"ok": True, "message": f"{svc['name']} durduruluyor..."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@services_bp.route("/api/services/<int:sid>/restart", methods=["POST"])
def restart_service(sid):
    conn = get_db()
    svc = conn.execute("SELECT * FROM services WHERE id = ?", (sid,)).fetchone()
    conn.close()
    if not svc:
        return jsonify({"ok": False, "error": "Service not found"}), 404

    try:
        subprocess.Popen(svc["command_restart"], shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify({"ok": True, "message": f"{svc['name']} yeniden başlatılıyor..."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@services_bp.route("/api/services/<int:sid>/config", methods=["GET"])
def get_config(sid):
    conn = get_db()
    svc = conn.execute("SELECT * FROM services WHERE id = ?", (sid,)).fetchone()
    conn.close()
    if not svc:
        return jsonify({"ok": False, "error": "Service not found"}), 404

    config_files = [f.strip() for f in (svc["config_files"] or "").split(",") if f.strip()]
    result = {}
    for cf in config_files:
        try:
            if os.path.isfile(cf):
                with open(cf, "r") as f:
                    result[cf] = f.read()
            else:
                result[cf] = f"# File not found: {cf}"
        except PermissionError:
            result[cf] = f"# Permission denied: {cf}"
        except Exception as e:
            result[cf] = f"# Error reading: {e}"

    return jsonify({"ok": True, "configs": result, "service_name": svc["name"]})


@services_bp.route("/api/services/<int:sid>/config", methods=["POST"])
def save_config(sid):
    conn = get_db()
    svc = conn.execute("SELECT * FROM services WHERE id = ?", (sid,)).fetchone()
    conn.close()
    if not svc:
        return jsonify({"ok": False, "error": "Service not found"}), 404

    data = request.get_json()
    file_path = data.get("file_path", "")
    content = data.get("content", "")

    if not file_path:
        return jsonify({"ok": False, "error": "No file path specified"}), 400

    config_files = [f.strip() for f in (svc["config_files"] or "").split(",") if f.strip()]
    if file_path not in config_files:
        return jsonify({"ok": False, "error": "Unauthorized file path"}), 403

    try:
        # Backup
        if os.path.isfile(file_path):
            shutil.copy2(file_path, file_path + ".bak")
        with open(file_path, "w") as f:
            f.write(content)
        return jsonify({"ok": True, "message": "Yapılandırma kaydedildi"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@services_bp.route("/api/services/<int:sid>/settings", methods=["GET"])
def get_service_settings(sid):
    conn = get_db()
    svc = conn.execute("SELECT * FROM services WHERE id = ?", (sid,)).fetchone()
    conn.close()
    if not svc:
        return jsonify({"ok": False, "error": "Service not found"}), 404

    return jsonify({"ok": True, "service": dict(svc)})


@services_bp.route("/api/services/<int:sid>/settings", methods=["POST"])
def update_service_settings(sid):
    data = request.get_json()
    conn = get_db()
    svc = conn.execute("SELECT * FROM services WHERE id = ?", (sid,)).fetchone()
    if not svc:
        conn.close()
        return jsonify({"ok": False, "error": "Service not found"}), 404

    allowed_fields = ["command_start", "command_stop", "command_restart",
                      "default_port", "config_files", "description"]
    updates = []
    values = []
    for field in allowed_fields:
        if field in data:
            updates.append(f"{field} = ?")
            values.append(data[field])

    if updates:
        values.append(sid)
        conn.execute(f"UPDATE services SET {', '.join(updates)} WHERE id = ?", values)
        conn.commit()

    conn.close()
    return jsonify({"ok": True, "message": "Ayarlar güncellendi"})

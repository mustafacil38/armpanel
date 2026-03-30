import os
import subprocess
import shutil
import psutil
import re
from flask import Blueprint, request, jsonify
from database import get_db

services_bp = Blueprint("services", __name__)

ALLOWED_CONFIG_DIRS = ["/etc/nginx", "/etc/php", "/etc/filebrowser", "/etc/ttyd", "/usr/local/etc"]


def _extract_port_from_configs(config_files_str, service_name, fallback_port):
    if not config_files_str:
        return fallback_port
    
    files = [f.strip() for f in config_files_str.split(",") if f.strip()]
    for file_path in files:
        if not os.path.isfile(file_path):
            continue
        try:
            with open(file_path, "r") as f:
                content = f.read()
            
            if service_name.lower() == "nginx":
                # Matches: listen 80; or listen 80 default_server; or listen [::]:80;
                match = re.search(r"listen\s+(?:\[::\]:)?(\d+)\s*(?:default_server|ssl|;)", content)
                if match:
                    return int(match.group(1))
            
            elif service_name.lower() == "php-fpm":
                # Matches: listen = 127.0.0.1:9000
                match = re.search(r"listen\s*=\s*(?:.*:)?(\d+)", content)
                if match:
                    return int(match.group(1))
                    
        except Exception:
            continue
    return fallback_port


def _update_port_in_configs(config_files_str, service_name, new_port):
    if not config_files_str:
        return
    
    files = [f.strip() for f in config_files_str.split(",") if f.strip()]
    for file_path in files:
        if not os.path.isfile(file_path):
            continue
        try:
            with open(file_path, "r") as f:
                content = f.read()
            
            new_content = content
            if service_name.lower() == "nginx":
                # Replace port in 'listen' lines
                new_content = re.sub(
                    r"(listen\s+(?:\[::\]:)?)\d+(\s*(?:default_server|ssl|;))",
                    f"\\1{new_port}\\2",
                    content
                )
            elif service_name.lower() == "php-fpm":
                # Replace port in 'listen =' lines
                new_content = re.sub(
                    r"(listen\s*=\s*(?:.*:)?)\d+",
                    f"\\1{new_port}",
                    content
                )
            
            if new_content != content:
                # Backup and write
                shutil.copy2(file_path, file_path + ".bak")
                with open(file_path, "w") as f:
                    f.write(new_content)
        except Exception as e:
            print(f"Error updating config {file_path}: {e}")


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
        # Extract real port from config if possible
        svc["default_port"] = _extract_port_from_configs(
            svc["config_files"], svc["name"], svc["default_port"]
        )
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

    service_dict = dict(svc)
    # Get current port from config if available
    service_dict["default_port"] = _extract_port_from_configs(
        svc["config_files"], svc["name"], svc["default_port"]
    )
    return jsonify({"ok": True, "service": service_dict})


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
    
    new_port = data.get("default_port")
    
    for field in allowed_fields:
        if field in data:
            updates.append(f"{field} = ?")
            values.append(data[field])

    if updates:
        values.append(sid)
        conn.execute(f"UPDATE services SET {', '.join(updates)} WHERE id = ?", values)
        conn.commit()

        # If port was updated, sync to config files
        if new_port is not None:
            config_files = data.get("config_files", svc["config_files"])
            _update_port_in_configs(config_files, svc["name"], new_port)

    conn.close()
    return jsonify({"ok": True, "message": "Ayarlar güncellendi"})

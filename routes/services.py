import os
import subprocess
import shutil
import psutil
import re
from flask import Blueprint, request, jsonify
from database import get_db

services_bp = Blueprint("services", __name__)

ALLOWED_CONFIG_DIRS = ["/etc/nginx", "/etc/php", "/etc/filebrowser", "/etc/ttyd", "/usr/local/etc"]


def _get_all_configs_content(config_files_str):
    if not config_files_str:
        return ""
    
    combined_content = ""
    files = [f.strip() for f in config_files_str.split(",") if f.strip()]
    for file_path in files:
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r") as f:
                    combined_content += f"\n# --- FILE: {file_path} ---\n"
                    combined_content += f.read()
            except Exception:
                continue
    return combined_content


def _extract_all_settings_from_configs(svc_name, config_files_str, current_db_stats):
    if not config_files_str:
        return current_db_stats
    
    settings = current_db_stats.copy()
    svc_name_lower = svc_name.lower()
    files = [f.strip() for f in config_files_str.split(",") if f.strip()]
    
    # Read each file separately to target specific settings to specific files
    file_contents = {}
    for fpath in files:
        if os.path.isfile(fpath):
            try:
                with open(fpath, "r") as f:
                    file_contents[fpath] = f.read()
            except Exception:
                continue

    if "nginx" in svc_name_lower:
        # Site config settings (Port, Root, Server Name) - usually in sites-available or conf.d
        site_content = ""
        for fpath, content in file_contents.items():
            if "nginx.conf" not in fpath:
                site_content += content
        
        if site_content:
            # Matches ACTIVE (uncommented) lines only
            match = re.search(r"^\s*listen\s+(?:\[::\]:)?(\d+)\s*(?:default_server|ssl|;)", site_content, re.MULTILINE)
            if match:
                settings["default_port"] = int(match.group(1))
            
            match = re.search(r"^\s*root\s+([^;]+);", site_content, re.MULTILINE)
            if match:
                settings["root_dir"] = match.group(1).strip()
                
            match = re.search(r"^\s*server_name\s+([^;]+);", site_content, re.MULTILINE)
            if match:
                settings["server_name"] = match.group(1).strip()
        
        # Global settings (Worker Processes) - usually in nginx.conf
        main_content = file_contents.get("/etc/nginx/nginx.conf", "")
        if not main_content: # Fallback: search all
            main_content = "\n".join(file_contents.values())
            
        match = re.search(r"^\s*worker_processes\s+([^;]+);", main_content, re.MULTILINE)
        if match:
            settings["worker_processes"] = match.group(1).strip()

    elif "php-fpm" in svc_name_lower or "php" in svc_name_lower:
        full_content = "\n".join(file_contents.values())
        # Port / Listen
        match = re.search(r"^\s*listen\s*=\s*(?:.*:)?(\d+)", full_content, re.MULTILINE)
        if match:
            settings["default_port"] = int(match.group(1))
        
        # PHP INI settings
        patterns = {
            "upload_max_filesize": r"^;?\s*upload_max_filesize\s*=\s*(.+)",
            "post_max_size": r"^;?\s*post_max_size\s*=\s*(.+)",
            "memory_limit": r"^;?\s*memory_limit\s*=\s*(.+)",
            "max_execution_time": r"^;?\s*max_execution_time\s*=\s*(.+)",
            "pm": r"^;?\s*pm\s*=\s*(.+)",
            "pm.max_children": r"^;?\s*pm\.max_children\s*=\s*(\d+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, full_content, re.MULTILINE)
            if match:
                settings[key] = match.group(1).strip()
                
    return settings


def _update_all_settings_in_configs(svc_name, config_files_str, new_settings):
    if not config_files_str:
        return
    
    files = [f.strip() for f in config_files_str.split(",") if f.strip()]
    svc_name_lower = svc_name.lower()
    
    for file_path in files:
        if not os.path.isfile(file_path):
            continue
        try:
            with open(file_path, "r") as f:
                content = f.read()
            
            new_content = content
            
            if "nginx" in svc_name_lower:
                # Target settings to appropriate files
                is_main_conf = "nginx.conf" in file_path
                
                if not is_main_conf:
                    # Site settings: listen, root, server_name
                    if "default_port" in new_settings:
                        new_content = re.sub(
                            r"(^\s*listen\s+(?:\[::\]:)?)\d+(\s*(?:default_server|ssl|;))",
                            f"\\1{new_settings['default_port']}\\2",
                            new_content, flags=re.MULTILINE
                        )
                    if "root_dir" in new_settings:
                        new_content = re.sub(
                            r"(^\s*root\s+)[^;]+(;)",
                            f"\\1{new_settings['root_dir']}\\2",
                            new_content, flags=re.MULTILINE
                        )
                    if "server_name" in new_settings:
                        new_content = re.sub(
                            r"(^\s*server_name\s+)[^;]+(;)",
                            f"\\1{new_settings['server_name']}\\2",
                            new_content, flags=re.MULTILINE
                        )
                else:
                    # Global settings: worker_processes, client_max_body_size
                    if "worker_processes" in new_settings:
                        new_content = re.sub(
                            r"(^\s*worker_processes\s+)[^;]+(;)",
                            f"\\1{new_settings['worker_processes']}\\2",
                            new_content, flags=re.MULTILINE
                        )
                    if "client_max_body_size" in new_settings:
                        new_content = re.sub(
                            r"(^\s*client_max_body_size\s+)[^;]+(;)",
                            f"\\1{new_settings['client_max_body_size']}\\2",
                            new_content, flags=re.MULTILINE
                        )
            
            elif "php-fpm" in svc_name_lower or "php" in svc_name_lower:
                # Port
                if "default_port" in new_settings:
                    new_content = re.sub(
                        r"(^\s*listen\s*=\s*(?:.*:)?)\d+",
                        f"\\1{new_settings['default_port']}",
                        new_content, flags=re.MULTILINE
                    )
                # PHP/FPM settings - matches even if commented with ; or #
                for key, val in new_settings.items():
                    if key in ["default_port", "config_files", "description", "sid"]: continue
                    # Safe regex escape and replace even commented lines
                    new_content = re.sub(
                        rf"(^[;#]?\s*{re.escape(key)}\s*=\s*).+",
                        f"{key} = {val}",
                        new_content, flags=re.MULTILINE
                    )
            
            if new_content != content:
                # Write directly without backup as requested
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
        # Extract real settings from all relevant configs
        svc = _extract_all_settings_from_configs(
            svc["name"], svc["config_files"], svc
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
    # Extract real settings from all relevant configs
    service_dict = _extract_all_settings_from_configs(
        svc["name"], svc["config_files"], service_dict
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

    # Standard DB fields
    allowed_db_fields = ["command_start", "command_stop", "command_restart",
                         "default_port", "config_files", "description"]
    updates = []
    values = []
    
    for field in allowed_db_fields:
        if field in data:
            updates.append(f"{field} = ?")
            values.append(data[field])

    if updates:
        values.append(sid)
        conn.execute(f"UPDATE services SET {', '.join(updates)} WHERE id = ?", values)
        conn.commit()

    # Sync all received settings to config files
    config_files = data.get("config_files", svc["config_files"])
    _update_all_settings_in_configs(svc["name"], config_files, data)

    conn.close()
    return jsonify({"ok": True, "message": "Ayarlar güncellendi"})

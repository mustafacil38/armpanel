import re
import os
import socket
import urllib.parse
import urllib.request
import subprocess
from flask import Blueprint, jsonify, request
from config import APPS_FILE, APPS_STORE_URL, TTYD_PORT

installer_bp = Blueprint("installer", __name__)


def get_local_ip():
    try:
        # Create a dummy socket to find the local IP address used for outbound connections
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 8.8.8.8 is Google's public DNS, but we don't actually need to connect
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _parse_apps_file():
    apps = []
    content = ""
    try:
        # Fetch the content from GitHub
        with urllib.request.urlopen(APPS_STORE_URL, timeout=10) as response:
            content = response.read().decode('utf-8')
    except Exception:
        # No local fallback as requested
        return []

    blocks = re.split(r"\n(?=\[)", content.strip())
    for block in blocks:
        lines = block.strip().split("\n")
        if not lines or not lines[0].startswith("["):
            continue
        name = lines[0].strip("[] \t")
        # Default values for more detailed view
        app = {"name": name, "version": "N/A", "category": "Genel", "description": "", "command": ""}
        for line in lines[1:]:
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip().lower()
                val = val.strip()
                if key == "version":
                    app["version"] = val
                elif key == "category":
                    app["category"] = val
                elif key == "description":
                    app["description"] = val
                elif key == "command":
                    app["command"] = val
        apps.append(app)

    return apps


@installer_bp.route("/api/installer/apps", methods=["GET"])
def list_apps():
    apps = _parse_apps_file()
    return jsonify(apps)


@installer_bp.route("/api/installer/install/<name>", methods=["POST"])
def install_app(name):
    apps = _parse_apps_file()
    target = None
    for app in apps:
        if app["name"].lower() == name.lower():
            target = app
            break

    if not target:
        return jsonify({"ok": False, "error": "Uygulama bulunamadı"}), 404

    # Return the ttyd URL with the command to execute
    # The frontend will open this in an iframe/popup
    local_ip = get_local_ip()
    ttyd_url = f"http://{local_ip}:{TTYD_PORT}"

    return jsonify({
        "ok": True,
        "app": target,
        "ttyd_url": ttyd_url,
        "message": f"{target['name']} kurulumu başlatılacak..."
    })


@installer_bp.route("/api/installer/send-command", methods=["POST"])
def send_command():
    data = request.get_json()
    command = data.get("command")

    if not command:
        return jsonify({"ok": False, "error": "Komut bulunamadı"}), 400

    try:
        # Inject command into tmux session 'armpanel'
        subprocess.run(["tmux", "send-keys", "-t", "armpanel", command, "C-m"], check=True)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Terminale komut gönderilemedi: {str(e)}"}), 500

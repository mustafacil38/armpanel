import re
import os
from flask import Blueprint, jsonify
from config import APPS_FILE, TTYD_PORT

installer_bp = Blueprint("installer", __name__)


def _parse_apps_file():
    apps = []
    if not os.path.isfile(APPS_FILE):
        return apps

    with open(APPS_FILE, "r") as f:
        content = f.read()

    blocks = re.split(r"\n(?=\[)", content.strip())
    for block in blocks:
        lines = block.strip().split("\n")
        if not lines or not lines[0].startswith("["):
            continue
        name = lines[0].strip("[] \t")
        app = {"name": name, "version": "", "command": ""}
        for line in lines[1:]:
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip().lower()
                val = val.strip()
                if key == "version":
                    app["version"] = val
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
    ttyd_url = f"http://localhost:{TTYD_PORT}"

    return jsonify({
        "ok": True,
        "app": target,
        "ttyd_url": ttyd_url,
        "message": f"{target['name']} kurulumu başlatılacak..."
    })

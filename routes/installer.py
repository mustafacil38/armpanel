import json
import os
import re
import socket
import subprocess
import urllib.request
from flask import Blueprint, jsonify, request
from config import TTYD_PORT

installer_bp = Blueprint("installer", __name__)

CASAOS_APPSTORE_API = "https://api.github.com/repos/IceWhaleTech/CasaOS-AppStore/contents/Apps"
CASAOS_RAW_BASE = "https://raw.githubusercontent.com/IceWhaleTech/CasaOS-AppStore/main/Apps"
CASAOS_CATEGORIES = "https://raw.githubusercontent.com/IceWhaleTech/CasaOS-AppStore/main/category-list.json"

_app_cache = []
_category_cache = []


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _github_get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "ArmPanel"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _raw_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ArmPanel"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def _extract_app_info(app_name, compose_text):
    """Extract key info from docker-compose.yml for the app store listing."""
    info = {
        "id": app_name,
        "name": app_name,
        "image": "",
        "port": "",
        "category": "Utilities",
        "description": "",
        "icon": "",
        "version": "latest",
        "compose_text": compose_text,
    }

    # Port from x-casaos port_map
    port_map = re.search(r"port_map:\s*[\"']?(\d+)", compose_text)
    if port_map:
        info["port"] = port_map.group(1)

    # Category
    cat_match = re.search(r"category:\s*(.+)", compose_text)
    if cat_match:
        info["category"] = cat_match.group(1).strip().strip("'\"")

    # Icon
    icon_match = re.search(r"icon:\s*(.+)", compose_text)
    if icon_match:
        info["icon"] = icon_match.group(1).strip().strip("'\"")

    # Description (tr_TR > en_US > en_us)
    desc_match = re.search(r"tr_TR:\s*\n((?:\s+\|.+\n?|\s+.+\n?)+)", compose_text)
    if not desc_match:
        desc_match = re.search(r"en_US:\s*\n((?:\s+\|.+\n?|\s+.+\n?)+)", compose_text)
    if not desc_match:
        desc_match = re.search(r"en_us:\s*\n((?:\s+\|.+\n?|\s+.+\n?)+)", compose_text)
    if desc_match:
        desc_lines = desc_match.group(1).split("\n")
        desc = []
        for dl in desc_lines:
            cleaned = dl.strip()
            if cleaned and not cleaned.startswith("|"):
                desc.append(cleaned)
        info["description"] = " ".join(desc)[:200]

    # Image (for reference)
    img_match = re.search(r"image:\s*(.+)", compose_text)
    if img_match:
        info["image"] = img_match.group(1).strip().strip("'\"")
        if ":" in info["image"]:
            info["version"] = info["image"].split(":")[-1]

    return info


def _fetch_casaos_apps(force=False):
    """Fetch all apps from CasaOS AppStore."""
    global _app_cache, _category_cache

    if _app_cache and not force:
        return _app_cache

    try:
        _category_cache = json.loads(_raw_get(CASAOS_CATEGORIES))
    except Exception:
        _category_cache = []

    try:
        dirs = _github_get(CASAOS_APPSTORE_API)
    except Exception:
        return _app_cache

    apps = []
    for entry in dirs:
        if entry.get("type") != "dir":
            continue
        app_name = entry["name"]
        try:
            compose_url = f"{CASAOS_RAW_BASE}/{app_name}/docker-compose.yml"
            compose_text = _raw_get(compose_url)
            app_info = _extract_app_info(app_name, compose_text)
            apps.append(app_info)
        except Exception:
            continue

    _app_cache = apps
    return apps


# ── Native App Definitions ──
# Her uygulama için native kurulum komutlari

NATIVE_APPS = {
    "Adminer": {
        "install": [
            "apt update -y && apt install -y adminer",
            "ln -sf /etc/adminer/adminer.conf /etc/nginx/sites-enabled/adminer.conf 2>/dev/null || true",
            "nginx -s reload 2>/dev/null || true",
        ],
        "uninstall": "apt remove -y adminer && apt autoremove -y",
        "check": "dpkg -l adminer 2>/dev/null | grep -q '^ii'",
        "service_start": "nginx -s reload 2>/dev/null || true",
        "service_stop": "",
        "port": "8080",
    },
    "Redis": {
        "install": "apt install -y redis-server",
        "uninstall": "apt remove -y redis-server && apt autoremove -y",
        "check": "dpkg -l redis-server 2>/dev/null | grep -q '^ii'",
        "service_start": "redis-server --daemonize yes",
        "service_stop": "redis-cli shutdown 2>/dev/null || pkill -f redis-server",
        "port": "6379",
    },
    "MariaDB": {
        "install": "apt install -y mariadb-server",
        "uninstall": "apt remove -y mariadb-server && apt autoremove -y",
        "check": "dpkg -l mariadb-server 2>/dev/null | grep -q '^ii'",
        "service_start": "mysqld_safe --datadir=/var/lib/mysql &",
        "service_stop": "mysqladmin shutdown 2>/dev/null || pkill -f mysqld",
        "port": "3306",
    },
    "Node-RED": {
        "install": [
            "apt install -y nodejs npm",
            "npm install -g --unsafe-perm node-red",
        ],
        "uninstall": "npm uninstall -g node-red",
        "check": "node-red --version &>/dev/null",
        "service_start": "node-red &",
        "service_stop": "pkill -f node-red",
        "port": "1880",
    },
    "Glances": {
        "install": "pip3 install glances",
        "uninstall": "pip3 uninstall -y glances",
        "check": "glances --version &>/dev/null",
        "service_start": "glances -w -p 61208 &",
        "service_stop": "pkill -f glances",
        "port": "61208",
    },
    "Hugo": {
        "install": "apt install -y hugo",
        "uninstall": "apt remove -y hugo && apt autoremove -y",
        "check": "hugo version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "1313",
    },
    "Gitea": {
        "install": [
            "wget -q https://dl.grafana.com/oss/release/grafana_10.0.0_arm64.deb -O /tmp/grafana.deb 2>/dev/null || true",
        ],
        "uninstall": "rm -f /usr/local/bin/gitea",
        "check": "gitea --version &>/dev/null",
        "service_start": "gitea web &",
        "service_stop": "pkill -f gitea",
        "port": "3000",
    },
    "Ollama": {
        "install": "curl -fsSL https://ollama.com/install.sh | sh",
        "uninstall": "rm -f /usr/local/bin/ollama",
        "check": "ollama --version &>/dev/null",
        "service_start": "ollama serve &",
        "service_stop": "pkill -f ollama",
        "port": "11434",
    },
    "ESPHome": {
        "install": "pip3 install esphome",
        "uninstall": "pip3 uninstall -y esphome",
        "check": "esphome version &>/dev/null",
        "service_start": "esphome dashboard /etc/esphome &",
        "service_stop": "pkill -f esphome",
        "port": "6052",
    },
    "Netdata": {
        "install": "apt install -y netdata",
        "uninstall": "apt remove -y netdata && apt autoremove -y",
        "check": "dpkg -l netdata 2>/dev/null | grep -q '^ii'",
        "service_start": "netdata &",
        "service_stop": "pkill -f netdata",
        "port": "19999",
    },
    "Grafana": {
        "install": [
            "apt install -y apt-transport-https software-properties-common wget",
            "wget -q -O /usr/share/keyrings/grafana.key https://apt.grafana.com/gpg.key",
            "echo 'deb [signed-by=/usr/share/keyrings/grafana.key] https://apt.grafana.com stable main' > /etc/apt/sources.list.d/grafana.list",
            "apt update -y && apt install -y grafana",
        ],
        "uninstall": "apt remove -y grafana && apt autoremove -y",
        "check": "dpkg -l grafana 2>/dev/null | grep -q '^ii'",
        "service_start": "grafana-server --homepath=/usr/share/grafana &",
        "service_stop": "pkill -f grafana-server",
        "port": "3000",
    },
}

# Docker image -> native app eslestirme
IMAGE_TO_NATIVE = {
    "adminer": "Adminer",
    "redis": "Redis",
    "mariadb": "MariaDB",
    "nodered/node-red": "Node-RED",
    "nicolargo/glances": "Glances",
    "ghcr.io/gohugoio/hugo": "Hugo",
    "go-gitea/gitea": "Gitea",
    "ollama/ollama": "Ollama",
    "esphome/esphome": "ESPHome",
    "netdata/netdata": "Netdata",
    "grafana/grafana": "Grafana",
}


def _find_native_app(app_id, compose_text):
    """CasaOS app_id veya image'dan native app tanimini bul."""
    # Once IMAGE_TO_NATIVE ile eslestir
    img_match = re.search(r"image:\s*(.+)", compose_text)
    if img_match:
        image = img_match.group(1).strip().strip("'\"").lower()
        for img_key, native_name in IMAGE_TO_NATIVE.items():
            if img_key in image:
                return native_name, NATIVE_APPS.get(native_name)

    # App adina gore ara
    for native_name, native_def in NATIVE_APPS.items():
        if native_name.lower() == app_id.lower():
            return native_name, native_def

    return None, None


def _run_cmd(cmd, timeout=300):
    """Shell komutu calistir."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def _is_installed(check_cmd):
    """Uygulamanin kurulu olup olmadigini kontrol et."""
    ok, _ = _run_cmd(check_cmd, timeout=10)
    return ok


# ── API Endpoints ──


@installer_bp.route("/api/installer/apps", methods=["GET"])
def list_apps():
    """List all apps from CasaOS AppStore."""
    apps = _fetch_casaos_apps()
    # Her app icin native kurulum destegi var mi ekle
    for app in apps:
        native_name, native_def = _find_native_app(app["id"], app.get("compose_text", ""))
        app["native_install"] = native_name is not None
        app["native_name"] = native_name or ""
    return jsonify(apps)


@installer_bp.route("/api/installer/categories", methods=["GET"])
def list_categories():
    try:
        cats = json.loads(_raw_get(CASAOS_CATEGORIES))
        return jsonify(cats)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@installer_bp.route("/api/installer/app/<app_id>", methods=["GET"])
def get_app_detail(app_id):
    apps = _fetch_casaos_apps()
    for app in apps:
        if app["id"] == app_id:
            native_name, native_def = _find_native_app(app_id, app.get("compose_text", ""))
            app["native_install"] = native_name is not None
            app["native_name"] = native_name or ""
            if native_def:
                app["native_port"] = native_def.get("port", "")
                app["native_installed"] = _is_installed(native_def["check"])
            return jsonify(app)
    return jsonify({"ok": False, "error": "App not found"}), 404


@installer_bp.route("/api/installer/install", methods=["POST"])
def install_app():
    """Install an app natively (apt/pip/curl)."""
    data = request.get_json()
    app_id = data.get("app_id")

    if not app_id:
        return jsonify({"ok": False, "error": "app_id required"}), 400

    apps = _fetch_casaos_apps()
    app = None
    for a in apps:
        if a["id"] == app_id:
            app = a
            break

    if not app:
        return jsonify({"ok": False, "error": "App not found"}), 404

    compose_text = app.get("compose_text", "")
    native_name, native_def = _find_native_app(app_id, compose_text)

    if not native_def:
        return jsonify({
            "ok": False,
            "error": f"'{app_id}' icin native kurulum tanimi yok. Sadece su uygulamalar destekleniyor: {', '.join(NATIVE_APPS.keys())}"
        }), 400

    if _is_installed(native_def["check"]):
        return jsonify({"ok": False, "error": f"{native_name} zaten kurulu"}), 409

    commands = native_def["install"]
    if isinstance(commands, str):
        commands = [commands]

    output = []
    for cmd in commands:
        ok, msg = _run_cmd(cmd, timeout=600)
        output.append({"cmd": cmd, "ok": ok, "output": msg[:500]})
        if not ok:
            return jsonify({
                "ok": False,
                "error": f"Kurulum basarisiz: {msg[:200]}",
                "step": cmd[:80],
                "output": output,
            }), 500

    # Servisi baslat
    if native_def.get("service_start"):
        _run_cmd(native_def["service_start"], timeout=30)

    # DB'ye kaydet
    from database import save_installed_app
    try:
        save_installed_app(
            app_id=app_id,
            name=native_name,
            port=native_def.get("port", ""),
            status="installed",
        )
    except Exception as e:
        print(f"[WARN] DB save failed: {e}")

    return jsonify({
        "ok": True,
        "message": f"{native_name} basariyla kuruldu",
        "name": native_name,
        "port": native_def.get("port", ""),
        "local_ip": get_local_ip(),
        "output": output,
    })


@installer_bp.route("/api/installer/uninstall", methods=["POST"])
def uninstall_app():
    """Uninstall a native app."""
    data = request.get_json()
    app_id = data.get("app_id")

    if not app_id:
        return jsonify({"ok": False, "error": "app_id required"}), 400

    apps = _fetch_casaos_apps()
    compose_text = ""
    for a in apps:
        if a["id"] == app_id:
            compose_text = a.get("compose_text", "")
            break

    native_name, native_def = _find_native_app(app_id, compose_text)
    if not native_def:
        return jsonify({"ok": False, "error": "App not found"}), 404

    if not _is_installed(native_def["check"]):
        return jsonify({"ok": False, "error": f"{native_name} kurulu degil"}), 404

    ok, msg = _run_cmd(native_def["uninstall"], timeout=300)
    if not ok:
        return jsonify({"ok": False, "error": f"Kaldirma basarisiz: {msg[:200]}"}), 500

    from database import delete_installed_app
    try:
        delete_installed_app(app_id)
    except Exception:
        pass

    return jsonify({"ok": True, "message": f"{native_name} kaldirildi"})


@installer_bp.route("/api/installer/installed", methods=["GET"])
def list_installed():
    """List all natively installed apps."""
    from database import list_installed_apps
    installed = list_installed_apps()

    # Check real status
    for app in installed:
        apps = _fetch_casaos_apps()
        compose_text = ""
        for a in apps:
            if a["id"] == app["app_id"]:
                compose_text = a.get("compose_text", "")
                break
        _, native_def = _find_native_app(app["app_id"], compose_text)
        if native_def:
            app["actually_installed"] = _is_installed(native_def["check"])

    return jsonify({"installed": installed})


@installer_bp.route("/api/installer/refresh", methods=["POST"])
def refresh_apps():
    """Force refresh the CasaOS AppStore cache."""
    global _app_cache
    _app_cache = []
    apps = _fetch_casaos_apps(force=True)
    return jsonify({"ok": True, "count": len(apps)})

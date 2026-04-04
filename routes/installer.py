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
    # ═══════════════════════════════════════════
    #  TEK BINARY (GitHub'dan ARM64 indir)
    # ═══════════════════════════════════════════
    "Adminer": {
        "desc": "MySQL/PostgreSQL/SQLite web yönetim arayüzü",
        "install": [
            "mkdir -p /var/www/html/adminer",
            "wget -q https://github.com/vrana/adminer/releases/download/v4.8.1/adminer-4.8.1.php -O /var/www/html/adminer/index.php",
        ],
        "uninstall": "rm -rf /var/www/html/adminer",
        "check": "test -f /var/www/html/adminer/index.php",
        "service_start": "",
        "service_stop": "",
        "port": "8080",
    },
    "Gitea": {
        "desc": "Hafif Git sunucusu (GitHub benzeri)",
        "install": [
            "GITEA_VER=$(curl -s https://api.github.com/repos/go-gitea/gitea/releases/latest | grep tag_name | cut -d'\"' -f4 | tr -d v)",
            "wget -q https://dl.grafana.com/oss/release/grafana_10.0.0_arm64.deb -O /tmp/gitea.deb 2>/dev/null || true",
        ],
        "uninstall": "rm -f /usr/local/bin/gitea",
        "check": "gitea --version &>/dev/null",
        "service_start": "gitea web &",
        "service_stop": "pkill -f gitea",
        "port": "3000",
    },
    "Hugo": {
        "desc": "Hızlı static site oluşturucu",
        "install": "apt install -y hugo 2>/dev/null || true",
        "uninstall": "apt remove -y hugo 2>/dev/null",
        "check": "hugo version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "1313",
    },
    "Caddy": {
        "desc": "Modern web sunucusu (otomatik HTTPS)",
        "install": [
            "curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null || true",
            "curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list 2>/dev/null || true",
            "apt update -y 2>/dev/null && apt install -y caddy 2>/dev/null || true",
        ],
        "uninstall": "apt remove -y caddy 2>/dev/null",
        "check": "caddy version &>/dev/null",
        "service_start": "caddy run --config /etc/caddy/Caddyfile &",
        "service_stop": "pkill -f caddy",
        "port": "2015",
    },
    "rclone": {
        "desc": "Cloud storage senkronizasyon aracı",
        "install": "curl https://rclone.org/install.sh | sh 2>/dev/null || true",
        "uninstall": "rm -f /usr/bin/rclone",
        "check": "rclone --version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "",
    },
    "btop": {
        "desc": "Görsel sistem monitörü (htop alternatifi)",
        "install": "apt install -y btop 2>/dev/null || true",
        "uninstall": "apt remove -y btop 2>/dev/null",
        "check": "btop --version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "",
    },
    "miniserve": {
        "desc": "Tek binary HTTP dosya sunucusu",
        "install": [
            "MINISERVE_VER=$(curl -s https://api.github.com/repos/svenstaro/miniserve/releases/latest | grep tag_name | cut -d'\"' -f4 | tr -d v)",
            "wget -q https://github.com/svenstaro/miniserve/releases/download/v${MINISERVE_VER}/miniserve-linux-aarch64 -O /usr/local/bin/miniserve 2>/dev/null || true",
            "chmod +x /usr/local/bin/miniserve",
        ],
        "uninstall": "rm -f /usr/local/bin/miniserve",
        "check": "test -x /usr/local/bin/miniserve",
        "service_start": "miniserve /var/www/html -p 8081 &",
        "service_stop": "pkill -f miniserve",
        "port": "8081",
    },
    "lazygit": {
        "desc": "Terminal tabanlı Git arayüzü",
        "install": [
            "LAZYGIT_VER=$(curl -s https://api.github.com/repos/jesseduffield/lazygit/releases/latest | grep tag_name | cut -d'\"' -f4 | tr -d v)",
            "wget -q https://github.com/jesseduffield/lazygit/releases/download/v${LAZYGIT_VER}/lazygit_${LAZYGIT_VER}_Linux_arm64.tar.gz -O /tmp/lazygit.tar.gz 2>/dev/null || true",
            "tar xzf /tmp/lazygit.tar.gz -C /tmp lazygit 2>/dev/null && mv /tmp/lazygit /usr/local/bin/ 2>/dev/null || true",
            "chmod +x /usr/local/bin/lazygit 2>/dev/null || true",
        ],
        "uninstall": "rm -f /usr/local/bin/lazygit",
        "check": "lazygit --version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "",
    },
    "fd": {
        "desc": "Hızlı find alternatifi",
        "install": "apt install -y fd-find 2>/dev/null || true",
        "uninstall": "apt remove -y fd-find 2>/dev/null",
        "check": "fdfind --version &>/dev/null || fd --version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "",
    },
    "ripgrep": {
        "desc": "Hızlı grep alternatifi",
        "install": "apt install -y ripgrep 2>/dev/null || true",
        "uninstall": "apt remove -y ripgrep 2>/dev/null",
        "check": "rg --version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "",
    },
    "mc": {
        "desc": "Midnight Commander — terminal dosya yöneticisi",
        "install": "apt install -y mc 2>/dev/null || true",
        "uninstall": "apt remove -y mc 2>/dev/null",
        "check": "mc --version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "",
    },
    # ═══════════════════════════════════════════
    #  PIP INSTALL (Python uygulamaları)
    # ═══════════════════════════════════════════
    "Glances": {
        "desc": "Web arayüzlü sistem izleme aracı",
        "install": "pip3 install glances",
        "uninstall": "pip3 uninstall -y glances",
        "check": "glances --version &>/dev/null",
        "service_start": "glances -w -p 61208 &",
        "service_stop": "pkill -f glances",
        "port": "61208",
    },
    "ESPHome": {
        "desc": "ESP32/ESP8266 IoT firmware yönetimi",
        "install": "pip3 install esphome",
        "uninstall": "pip3 uninstall -y esphome",
        "check": "esphome version &>/dev/null",
        "service_start": "esphome dashboard /etc/esphome &",
        "service_stop": "pkill -f esphome",
        "port": "6052",
    },
    "Home Assistant": {
        "desc": "Akıllı ev otomasyon platformu",
        "install": "pip3 install homeassistant",
        "uninstall": "pip3 uninstall -y homeassistant",
        "check": "hass --version &>/dev/null",
        "service_start": "hass &",
        "service_stop": "pkill -f hass",
        "port": "8123",
    },
    "Jupyter": {
        "desc": "Python notebook — interaktif kod çalıştırma",
        "install": "pip3 install jupyterlab",
        "uninstall": "pip3 uninstall -y jupyterlab",
        "check": "jupyter --version &>/dev/null",
        "service_start": "jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root &",
        "service_stop": "pkill -f jupyter",
        "port": "8888",
    },
    "MkDocs": {
        "desc": "Markdown ile dokümantasyon sitesi oluşturucu",
        "install": "pip3 install mkdocs mkdocs-material",
        "uninstall": "pip3 uninstall -y mkdocs mkdocs-material",
        "check": "mkdocs --version &>/dev/null",
        "service_start": "mkdocs serve -a 0.0.0.0:8000 &",
        "service_stop": "pkill -f mkdocs",
        "port": "8000",
    },
    "speedtest-cli": {
        "desc": "İnternet hız testi",
        "install": "pip3 install speedtest-cli",
        "uninstall": "pip3 uninstall -y speedtest-cli",
        "check": "speedtest-cli --version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "",
    },
    "yt-dlp": {
        "desc": "YouTube ve diğer sitelerden video indirme",
        "install": "pip3 install yt-dlp",
        "uninstall": "pip3 uninstall -y yt-dlp",
        "check": "yt-dlp --version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "",
    },
    "httpie": {
        "desc": "Modern HTTP istemcisi (curl alternatifi)",
        "install": "pip3 install httpie",
        "uninstall": "pip3 uninstall -y httpie",
        "check": "http --version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "",
    },
    "localtunnel": {
        "desc": "Ngrok alternatifi — local sunucuyu dışarıya aç",
        "install": "pip3 install localtunnel",
        "uninstall": "pip3 uninstall -y localtunnel",
        "check": "localtunnel --version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "",
    },
    # ═══════════════════════════════════════════
    #  NPM INSTALL -g (Node.js uygulamaları)
    # ═══════════════════════════════════════════
    "Node-RED": {
        "desc": "Görsel IoT programlama arayüzü",
        "install": [
            "apt install -y nodejs npm 2>/dev/null || true",
            "npm install -g --unsafe-perm node-red 2>/dev/null",
        ],
        "uninstall": "npm uninstall -g node-red 2>/dev/null",
        "check": "node-red --version &>/dev/null",
        "service_start": "node-red &",
        "service_stop": "pkill -f node-red",
        "port": "1880",
    },
    "http-server": {
        "desc": "Basit HTTP dosya sunucusu (Node.js)",
        "install": [
            "apt install -y nodejs npm 2>/dev/null || true",
            "npm install -g http-server 2>/dev/null",
        ],
        "uninstall": "npm uninstall -g http-server 2>/dev/null",
        "check": "http-server --version &>/dev/null",
        "service_start": "http-server /var/www/html -p 8082 -c-1 &",
        "service_stop": "pkill -f http-server",
        "port": "8082",
    },
    "PM2": {
        "desc": "Node.js process manager (daemon)",
        "install": [
            "apt install -y nodejs npm 2>/dev/null || true",
            "npm install -g pm2 2>/dev/null",
        ],
        "uninstall": "npm uninstall -g pm2 2>/dev/null",
        "check": "pm2 --version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "",
    },
    "live-server": {
        "desc": "Canlı yeniden yüklemeli geliştirme sunucusu",
        "install": [
            "apt install -y nodejs npm 2>/dev/null || true",
            "npm install -g live-server 2>/dev/null",
        ],
        "uninstall": "npm uninstall -g live-server 2>/dev/null",
        "check": "live-server --version &>/dev/null",
        "service_start": "live-server /var/www/html --port=8084 &",
        "service_stop": "pkill -f live-server",
        "port": "8084",
    },
    # ═══════════════════════════════════════════
    #  CURL | SH (Resmi kurulum betikleri)
    # ═══════════════════════════════════════════
    "Ollama": {
        "desc": "Yerel AI/LLM çalıştırma aracı",
        "install": "curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null || true",
        "uninstall": "rm -f /usr/local/bin/ollama",
        "check": "ollama --version &>/dev/null",
        "service_start": "ollama serve &",
        "service_stop": "pkill -f ollama",
        "port": "11434",
    },
    "Netdata": {
        "desc": "Gerçek zamanlı sistem performans izleme",
        "install": "curl -fsSL https://my-netdata.io/kickstart.sh | sh 2>/dev/null || apt install -y netdata 2>/dev/null || true",
        "uninstall": "pkill -f netdata; apt remove -y netdata 2>/dev/null",
        "check": "netdata --version &>/dev/null || dpkg -l netdata 2>/dev/null | grep -q '^ii'",
        "service_start": "netdata &",
        "service_stop": "pkill -f netdata",
        "port": "19999",
    },
    # ═══════════════════════════════════════════
    #  APT + MANUEL BAŞLATMA (servisler &)
    # ═══════════════════════════════════════════
    "Redis": {
        "desc": "Hızlı in-memory veritabanı",
        "install": "apt install -y redis-server 2>/dev/null || true",
        "uninstall": "pkill -f redis-server; apt remove -y redis-server 2>/dev/null",
        "check": "redis-cli ping 2>/dev/null | grep -q PONG || dpkg -l redis-server 2>/dev/null | grep -q '^ii'",
        "service_start": "redis-server --daemonize yes",
        "service_stop": "pkill -f redis-server",
        "port": "6379",
    },
    "SQLite": {
        "desc": "Hafif dosya tabanlı veritabanı",
        "install": "apt install -y sqlite3 2>/dev/null || true",
        "uninstall": "apt remove -y sqlite3 2>/dev/null",
        "check": "sqlite3 --version &>/dev/null",
        "service_start": "",
        "service_stop": "",
        "port": "",
    },
    "OpenSSH": {
        "desc": "SSH sunucusu (uzaktan erişim)",
        "install": "apt install -y openssh-server 2>/dev/null || true",
        "uninstall": "pkill -f sshd; apt remove -y openssh-server 2>/dev/null",
        "check": "dpkg -l openssh-server 2>/dev/null | grep -q '^ii'",
        "service_start": "mkdir -p /run/sshd && /usr/sbin/sshd &",
        "service_stop": "pkill -f sshd",
        "port": "22",
    },
}

# Docker image -> native app eslestirme
IMAGE_TO_NATIVE = {
    "adminer": "Adminer",
    "redis": "Redis",
    "nodered/node-red": "Node-RED",
    "nicolargo/glances": "Glances",
    "ghcr.io/gohugoio/hugo": "Hugo",
    "go-gitea/gitea": "Gitea",
    "ollama/ollama": "Ollama",
    "esphome/esphome": "ESPHome",
    "netdata/netdata": "Netdata",
    "homeassistant/home-assistant": "Home Assistant",
    "jupyter/minimal-notebook": "Jupyter",
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
    """Native uygulama listesini dondur. CasaOS'tan ikon/aciklama zenginlestirilir."""
    apps = _fetch_casaos_apps()
    # CasaOS app'lerini map'le (icon, description, category icin)
    casaos_map = {}
    for a in apps:
        casaos_map[a["id"].lower()] = a

    result = []
    for native_name, native_def in NATIVE_APPS.items():
        # CasaOS'tan eslesen app bul (icon, category icin)
        casaos_app = None
        for app_id_lower, app_data in casaos_map.items():
            if app_id_lower == native_name.lower():
                casaos_app = app_data
                break
        if not casaos_app:
            for img_key, n_name in IMAGE_TO_NATIVE.items():
                if n_name == native_name:
                    for app_id_lower, app_data in casaos_map.items():
                        if img_key in app_data.get("image", "").lower():
                            casaos_app = app_data
                            break
                    break

        app_info = {
            "id": native_name,
            "name": native_name,
            "desc": native_def.get("desc", ""),
            "port": native_def.get("port", ""),
            "category": "Araç",
            "icon": "",
            "description": "",
            "version": "latest",
            "native_install": True,
            "native_name": native_name,
        }

        if casaos_app:
            app_info["icon"] = casaos_app.get("icon", "")
            app_info["description"] = casaos_app.get("description", "")
            if casaos_app.get("category"):
                app_info["category"] = casaos_app["category"]

        result.append(app_info)

    return jsonify(result)


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

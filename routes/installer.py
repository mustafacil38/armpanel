import json
import os
import re
import socket
import subprocess
import urllib.request
import yaml
from flask import Blueprint, jsonify, request
from config import TTYD_PORT

installer_bp = Blueprint("installer", __name__)

CASAOS_APPSTORE_API = "https://api.github.com/repos/IceWhaleTech/CasaOS-AppStore/contents/Apps"
CASAOS_RAW_BASE = "https://raw.githubusercontent.com/IceWhaleTech/CasaOS-AppStore/main/Apps"
CASAOS_CATEGORIES = "https://raw.githubusercontent.com/IceWhaleTech/CasaOS-AppStore/main/category-list.json"

# Local cache for app list (populated on first request)
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
    """Make a GET request to GitHub API with proper headers."""
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "ArmPanel"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _raw_get(url):
    """Fetch raw content from GitHub."""
    req = urllib.request.Request(url, headers={"User-Agent": "ArmPanel"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def _parse_yaml_simple(text):
    """Minimal YAML parser for docker-compose.yml files.
    Handles the subset of YAML used in CasaOS manifests."""
    result = {}
    lines = text.split("\n")
    stack = [(result, -1)]  # (dict, indent_level)

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        # Pop stack to find parent
        while len(stack) > 1 and stack[-1][1] >= indent:
            stack.pop()

        parent = stack[-1][0]

        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()

            if val:
                # Remove quotes
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                parent[key] = val
            else:
                new_dict = {}
                parent[key] = new_dict
                stack.append((new_dict, indent))
        elif stripped.startswith("- "):
            # List item
            val = stripped[2:].strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if not isinstance(parent, list):
                # Convert parent dict to have a list - shouldn't happen in well-formed compose
                continue

    return result


def _extract_app_info(app_name, compose_text):
    """Extract key info from docker-compose.yml for the app store listing."""
    info = {
        "id": app_name,
        "name": app_name,
        "image": "",
        "container_name": app_name.lower(),
        "port": "",
        "category": "Utilities",
        "description": "",
        "icon": "",
        "version": "latest",
        "environment": [],
        "volumes": [],
        "compose_text": compose_text,
    }

    try:
        compose = yaml.safe_load(compose_text)
    except yaml.YAMLError:
        compose = None

    if compose and "services" in compose:
        service_name = list(compose["services"].keys())[0]
        service = compose["services"][service_name]

        info["image"] = service.get("image", "")
        info["container_name"] = service.get("container_name", app_name.lower())

        # Port extraction
        ports = service.get("ports", [])
        if ports:
            first = str(ports[0])
            if ":" in first:
                info["port"] = first.split(":")[0].replace("'", "").replace('"', "")
            else:
                info["port"] = first.replace("'", "").replace('"', "")

        # Env extraction
        env = service.get("environment", {})
        if isinstance(env, dict):
            info["environment"] = [f"{k}={v}" for k, v in env.items()]
        elif isinstance(env, list):
            info["environment"] = [str(e) for e in env]

        # Volumes
        volumes = service.get("volumes", [])
        info["volumes"] = [str(v) for v in volumes]

    # Fallback: regex for description/icon/category from compose text
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

    cat_match = re.search(r"category:\s*(.+)", compose_text)
    if cat_match:
        info["category"] = cat_match.group(1).strip().strip("'\"")

    icon_match = re.search(r"icon:\s*(.+)", compose_text)
    if icon_match:
        info["icon"] = icon_match.group(1).strip().strip("'\"")

    # x-casaos port_map fallback
    if not info["port"]:
        port_map = re.search(r"port_map:\s*[\"']?(\d+)", compose_text)
        if port_map:
            info["port"] = port_map.group(1)

    if ":" in info["image"]:
        info["version"] = info["image"].split(":")[-1]

    return info


def _fetch_casaos_apps(force=False):
    """Fetch all apps from CasaOS AppStore."""
    global _app_cache, _category_cache

    if _app_cache and not force:
        return _app_cache

    # Fetch categories
    try:
        _category_cache = json.loads(_raw_get(CASAOS_CATEGORIES))
    except Exception:
        _category_cache = []

    # Fetch app directories
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
            if app_info["image"]:  # Only add if we found an image
                apps.append(app_info)
        except Exception:
            continue

    _app_cache = apps
    return apps


def _run_udocker(args, timeout=300):
    """Run a udocker command as the 'udocker' user."""
    inner_cmd = "udocker " + " ".join(args)
    cmd = ["su", "-", "udocker", "-c", inner_cmd]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", "udocker or su not found."
    except Exception as e:
        return -1, "", str(e)


def _udocker_setup():
    """Run udocker setup with P1 execmode (proot-compatible)."""
    rc, out, err = _run_udocker(["setup", "--execmode=P1"], timeout=60)
    return rc == 0, out + err


def _udocker_pull(image):
    """Pull a Docker image using udocker."""
    rc, out, err = _run_udocker(["pull", image], timeout=600)
    return rc == 0, out + err


def _udocker_create(name, image, extra_args=None):
    """Create a container. extra_args should be uDocker flags (--port, --env, --volume)."""
    cmd = ["create", f"--name={name}"]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(image)
    rc, out, err = _run_udocker(cmd, timeout=120)
    return rc == 0, out + err


def _udocker_start(name):
    """Start a container.

    Proot ortamında --execmode=P1 ile başlatmak daha uyumludur.
    """
    rc, out, err = _run_udocker(["start", name], timeout=60)
    return rc == 0, out + err


def _udocker_stop(name):
    """Stop a container."""
    rc, out, err = _run_udocker(["stop", name], timeout=30)
    return rc == 0, out + err


def _udocker_rm(name):
    """Remove a container."""
    rc, out, err = _run_udocker(["rm", name], timeout=30)
    return rc == 0, out + err


def _udocker_rmi(image):
    """Remove an image."""
    rc, out, err = _run_udocker(["rmi", image], timeout=30)
    return rc == 0, out + err


def _udocker_ps():
    """List containers."""
    rc, out, err = _run_udocker(["ps"], timeout=10)
    return out if rc == 0 else err


def _udocker_images():
    """List images."""
    rc, out, err = _run_udocker(["images"], timeout=10)
    return out if rc == 0 else err


def _udocker_logs(name, tail=100):
    """Get container logs."""
    rc, out, err = _run_udocker(["logs", name], timeout=30)
    return out + err


def _parse_compose_for_udocker(compose_text, app_id, port_override=None):
    """Parse docker-compose.yml with pyyaml and generate uDocker commands.

    uDocker CLI syntax:
      --port=HOST:CONTAINER
      --env=KEY=VALUE
      --volume=HOST:CONTAINER
      --execmode=P1 (setup komutunda, create'da degil)
    """
    try:
        compose = yaml.safe_load(compose_text)
    except yaml.YAMLError as e:
        return None, f"YAML parse error: {e}"

    if not compose or "services" not in compose:
        return None, "No services found in compose file"

    service_name = list(compose["services"].keys())[0]
    service = compose["services"][service_name]

    image = service.get("image", "")
    if not image:
        return None, "Image not found in compose file"

    container_name = service.get("container_name", app_id.lower().replace(" ", "_").replace("-", "_"))

    # --- Environment ---
    env_args = []
    env = service.get("environment", {})
    if isinstance(env, dict):
        for k, v in env.items():
            env_args.append(f"--env={k}={v}")
    elif isinstance(env, list):
        for item in env:
            item = str(item).strip()
            if "=" in item:
                env_args.append(f"--env={item}")
            else:
                env_args.append(f"--env={item}")

    # --- Ports ---
    port_args = []
    first_port = ""
    ports = service.get("ports", [])
    if isinstance(ports, list):
        for p in ports:
            p_str = str(p).replace("'", "").replace('"', "")
            if ":" in p_str:
                parts = p_str.split(":")
                host_port = parts[-2] if len(parts) >= 2 else parts[0]
                container_port = parts[-1]
                first_port = first_port or host_port
                port_args.append(f"--port={host_port}:{container_port}")
            else:
                first_port = first_port or p_str
                port_args.append(f"--port={p_str}:{p_str}")

    # x-casaos port_map fallback
    if not first_port:
        x_casaos = compose.get("x-casaos", {})
        if isinstance(x_casaos, dict):
            port_map = x_casaos.get("port_map", "")
            if port_map:
                first_port = str(port_map)
                port_args.append(f"--port={first_port}:{first_port}")

    if port_override:
        for i in range(len(port_args)):
            if port_args[i].startswith("--port="):
                old = port_args[i].split("=", 1)[1]
                if ":" in old:
                    container_p = old.split(":")[1]
                else:
                    container_p = old
                port_args[i] = f"--port={port_override}:{container_p}"
                first_port = str(port_override)
                break

    # --- Volumes ---
    vol_args = []
    volumes = service.get("volumes", [])
    if isinstance(volumes, list):
        for v in volumes:
            if isinstance(v, dict):
                src = str(v.get("source", ""))
                tgt = str(v.get("target", ""))
                if src and tgt and not src.startswith("/dev/") and not src.startswith("/opt/vc"):
                    vol_args.append(f"--volume={src}:{tgt}")
            elif isinstance(v, str) and ":" in v:
                parts = v.split(":")
                src, tgt = parts[0], parts[1]
                if not src.startswith("/dev/") and not src.startswith("/opt/vc"):
                    vol_args.append(f"--volume={src}:{tgt}")

    create_args = port_args + env_args + vol_args

    commands = [
        f"udocker pull {image}",
        f"udocker create --name={container_name} {' '.join(create_args)} {image}",
        f"udocker start {container_name}",
    ]

    return {
        "image": image,
        "container_name": container_name,
        "commands": commands,
        "create_args": create_args,
        "port": first_port,
    }, None


# ── API Endpoints ──


@installer_bp.route("/api/installer/apps", methods=["GET"])
def list_apps():
    """List all apps from CasaOS AppStore."""
    apps = _fetch_casaos_apps()
    return jsonify(apps)


@installer_bp.route("/api/installer/categories", methods=["GET"])
def list_categories():
    """List categories from CasaOS AppStore."""
    try:
        cats = json.loads(_raw_get(CASAOS_CATEGORIES))
        return jsonify(cats)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@installer_bp.route("/api/installer/app/<app_id>", methods=["GET"])
def get_app_detail(app_id):
    """Get detailed info for a specific app."""
    apps = _fetch_casaos_apps()
    for app in apps:
        if app["id"] == app_id:
            # Parse compose for udocker commands
            parsed, err = _parse_compose_for_udocker(app["compose_text"], app_id)
            if parsed:
                app["install_info"] = parsed
            return jsonify(app)
    return jsonify({"ok": False, "error": "App not found"}), 404


@installer_bp.route("/api/installer/install", methods=["POST"])
def install_app():
    """Install an app using udocker. Pulls image, creates container, and starts it."""
    data = request.get_json()
    app_id = data.get("app_id")
    port_override = data.get("port")

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

    parsed, err = _parse_compose_for_udocker(app["compose_text"], app_id, port_override)
    if not parsed:
        return jsonify({"ok": False, "error": err or "Could not parse compose file"}), 400

    # Check if container already exists
    ps_output = _udocker_ps()
    if app["container_name"] in ps_output:
        return jsonify({
            "ok": False,
            "error": f"Container '{app['container_name']}' already exists. Remove it first."
        }), 409

    # Step 1: Pull
    ok, msg = _udocker_pull(parsed["image"])
    if not ok:
        return jsonify({"ok": False, "error": f"Pull failed: {msg}", "step": "pull"}), 500

    # Step 2: Create
    ok, msg = _udocker_create(app["container_name"], parsed["image"], parsed["create_args"])
    if not ok:
        return jsonify({"ok": False, "error": f"Create failed: {msg}", "step": "create"}), 500

    # Step 3: Start
    ok, msg = _udocker_start(app["container_name"])
    if not ok:
        return jsonify({"ok": False, "error": f"Start failed: {msg}", "step": "start"}), 500

    # Step 4: Save to database
    try:
        compose = yaml.safe_load(app["compose_text"])
        service = compose.get("services", {})
        first_svc = list(service.values())[0] if service else {}
        env_dict = {}
        env_raw = first_svc.get("environment", {})
        if isinstance(env_raw, dict):
            env_dict = env_raw
        elif isinstance(env_raw, list):
            for item in env_raw:
                if "=" in str(item):
                    k, v = str(item).split("=", 1)
                    env_dict[k.strip()] = v.strip()

        vol_list = []
        for v in first_svc.get("volumes", []):
            if isinstance(v, dict):
                src, tgt = v.get("source", ""), v.get("target", "")
                if src and tgt and not str(src).startswith("/dev/"):
                    vol_list.append((str(src), str(tgt)))
            elif isinstance(v, str) and ":" in v:
                parts = v.split(":")
                if not parts[0].startswith("/dev/"):
                    vol_list.append((parts[0], parts[1]))

        from database import save_container
        save_container(
            app_id=app_id,
            name=parsed["container_name"],
            image=parsed["image"],
            port=parsed["port"],
            exec_mode="P1",
            create_args=parsed["create_args"],
            compose_text=app["compose_text"],
            env_vars=env_dict,
            volumes=vol_list,
        )
    except Exception as e:
        print(f"[WARN] Container DB save failed: {e}")

    return jsonify({
        "ok": True,
        "message": f"{app['name']} installed and started successfully",
        "container_name": app["container_name"],
        "port": parsed["port"],
        "local_ip": get_local_ip(),
    })


@installer_bp.route("/api/installer/containers", methods=["GET"])
def list_containers():
    """List all udocker containers with DB info merged."""
    output = _udocker_ps()
    containers = []
    lines = output.strip().split("\n")
    if len(lines) > 1:
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 3:
                c = {
                    "container_id": parts[0],
                    "name": parts[1] if len(parts) > 1 else "",
                    "image": parts[2] if len(parts) > 2 else "",
                    "status": parts[3] if len(parts) > 3 else "",
                }
                # Merge DB info
                from database import get_container
                db_info = get_container(c["name"])
                if db_info:
                    c["app_id"] = db_info.get("app_id", "")
                    c["port"] = db_info.get("port", "")
                    c["env"] = db_info.get("env", {})
                    c["volumes"] = db_info.get("volumes", [])
                containers.append(c)

    # Also include DB-only containers (stopped/not showing in ps)
    from database import list_containers_db
    db_containers = list_containers_db()
    db_names = {c["name"] for c in containers}
    for db_c in db_containers:
        if db_c["name"] not in db_names:
            db_c["container_id"] = ""
            containers.append(db_c)

    return jsonify({"containers": containers, "raw": output})


@installer_bp.route("/api/installer/containers/<name>/start", methods=["POST"])
def start_container(name):
    """Start a udocker container."""
    ok, msg = _udocker_start(name)
    if ok:
        from database import update_container_status
        update_container_status(name, "running")
    return jsonify({"ok": ok, "message": msg})


@installer_bp.route("/api/installer/containers/<name>/stop", methods=["POST"])
def stop_container(name):
    """Stop a udocker container."""
    ok, msg = _udocker_stop(name)
    if ok:
        from database import update_container_status
        update_container_status(name, "stopped")
    return jsonify({"ok": ok, "message": msg})


@installer_bp.route("/api/installer/containers/<name>", methods=["DELETE"])
def remove_container(name):
    """Remove a udocker container."""
    ok, msg = _udocker_rm(name)
    if ok:
        from database import delete_container_db
        delete_container_db(name)
    return jsonify({"ok": ok, "message": msg})


@installer_bp.route("/api/installer/containers/<name>/logs", methods=["GET"])
def container_logs(name):
    """Get container logs."""
    logs = _udocker_logs(name)
    return jsonify({"logs": logs})


@installer_bp.route("/api/installer/images", methods=["GET"])
def list_images():
    """List all udocker images."""
    output = _udocker_images()
    images = []
    lines = output.strip().split("\n")
    if len(lines) > 1:
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 3:
                images.append({
                    "image_id": parts[0],
                    "name": parts[1],
                    "tag": parts[2] if len(parts) > 2 else "",
                })
    return jsonify({"images": images, "raw": output})


@installer_bp.route("/api/installer/refresh", methods=["POST"])
def refresh_apps():
    """Force refresh the CasaOS AppStore cache."""
    global _app_cache
    _app_cache = []
    apps = _fetch_casaos_apps(force=True)
    return jsonify({"ok": True, "count": len(apps)})

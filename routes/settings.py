import os
import subprocess
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash
from database import get_db
from config import GITHUB_REPO, TTYD_PORT

settings_bp = Blueprint("settings", __name__)


# ── User management ──

@settings_bp.route("/api/settings/user", methods=["GET"])
def get_user():
    if "user_id" not in session:
        return jsonify({"ok": False}), 401
    return jsonify({"ok": True, "username": session["username"]})


@settings_bp.route("/api/settings/user", methods=["POST"])
def update_user():
    if "user_id" not in session:
        return jsonify({"ok": False}), 401

    data = request.get_json()
    new_username = data.get("username", "").strip()
    new_password = data.get("password", "").strip()

    if not new_username:
        return jsonify({"ok": False, "error": "Kullanıcı adı boş olamaz"}), 400

    conn = get_db()
    if new_password:
        conn.execute(
            "UPDATE users SET username = ?, password_hash = ? WHERE id = ?",
            (new_username, generate_password_hash(new_password), session["user_id"]),
        )
    else:
        conn.execute(
            "UPDATE users SET username = ? WHERE id = ?",
            (new_username, session["user_id"]),
        )
    conn.commit()
    conn.close()

    session["username"] = new_username
    return jsonify({"ok": True, "message": "Kullanıcı bilgileri güncellendi"})


# ── Cloudflare Tunnel ──

@settings_bp.route("/api/settings/cloudflare", methods=["GET"])
def get_cloudflare():
    conn = get_db()
    token_row = conn.execute("SELECT value FROM settings WHERE key = 'cf_token'").fetchone()
    conn.close()

    token = token_row["value"] if token_row else ""

    # Check if cloudflared is running
    is_running = False
    try:
        result = subprocess.run(["pgrep", "-f", "cloudflared"], capture_output=True)
        is_running = result.returncode == 0
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "token": token,
        "is_running": is_running,
    })


@settings_bp.route("/api/settings/cloudflare", methods=["POST"])
def save_cloudflare():
    data = request.get_json()
    token = data.get("token", "").strip()

    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('cf_token', ?)", (token,)
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "message": "Cloudflare token kaydedildi"})


@settings_bp.route("/api/settings/cloudflare/start", methods=["POST"])
def start_cloudflare():
    conn = get_db()
    token_row = conn.execute("SELECT value FROM settings WHERE key = 'cf_token'").fetchone()
    conn.close()

    if not token_row or not token_row["value"]:
        return jsonify({"ok": False, "error": "Cloudflare token ayarlanmamış"}), 400

    token = token_row["value"]
    try:
        subprocess.Popen(
            f"cloudflared tunnel --no-autoupdate run --token {token}",
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return jsonify({"ok": True, "message": "Cloudflare Tunnel başlatılıyor..."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@settings_bp.route("/api/settings/cloudflare/stop", methods=["POST"])
def stop_cloudflare():
    try:
        subprocess.run(["pkill", "-f", "cloudflared"], capture_output=True)
        return jsonify({"ok": True, "message": "Cloudflare Tunnel durduruldu"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── GitHub Update ──

@settings_bp.route("/api/settings/update", methods=["POST"])
def github_update():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        # Check if .git exists
        if os.path.isdir(os.path.join(base_dir, ".git")):
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=base_dir, capture_output=True, text=True, timeout=60,
            )
        else:
            result = subprocess.run(
                ["git", "clone", GITHUB_REPO, "."],
                cwd=base_dir, capture_output=True, text=True, timeout=120,
            )

        output = result.stdout + result.stderr
        ok = result.returncode == 0

        return jsonify({
            "ok": ok,
            "message": "Güncelleme tamamlandı" if ok else "Güncelleme başarısız",
            "output": output,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "Güncelleme zaman aşımına uğradı"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@settings_bp.route("/api/settings/ttyd-port", methods=["GET"])
def get_ttyd_port():
    return jsonify({"ok": True, "port": TTYD_PORT})

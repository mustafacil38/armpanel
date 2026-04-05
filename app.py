from flask import Flask, send_from_directory, session, jsonify, redirect
from config import SECRET_KEY, PANEL_HOST, PANEL_PORT
from database import init_db, migrate_db
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.services import services_bp
from routes.settings import settings_bp
from routes.store import store_bp
import os

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)
app.secret_key = SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(services_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(store_bp)


@app.before_request
def require_login():
    from flask import request
    # Exempt paths
    exempt = ["/api/auth/login", "/api/auth/check", "/static/", "/favicon.ico"]
    path = request.path
    if any(path.startswith(e) for e in exempt):
        return
    if path == "/" or path == "/index.html":
        return
    if path.startswith("/api/") and "user_id" not in session:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401


@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/favicon.ico")
def favicon():
    return "", 204


def auto_start_all():
    """Panel açılışında is_autostart = 1 olan servisleri başlatır."""
    import subprocess
    from database import get_db
    
    print("\n  [AUTO-START] Servisler kontrol ediliyor...")
    conn = get_db()
    
    # 1. Normal servisler
    try:
        services = conn.execute("SELECT name, command_start FROM services WHERE is_autostart = 1").fetchall()
        for svc in services:
            print(f"  [AUTO-START] {svc['name']} başlatılıyor...")
            subprocess.Popen(svc["command_start"], shell=True, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"  [ERROR] Servis auto-start hatası: {e}")

    # 2. Cloudflare Tunnel
    try:
        token_row = conn.execute("SELECT value FROM settings WHERE key = 'cf_token'").fetchone()
        auto_row = conn.execute("SELECT value FROM settings WHERE key = 'cf_autostart'").fetchone()
        if token_row and token_row["value"] and auto_row and auto_row["value"] == "1":
            print(f"  [AUTO-START] Cloudflare Tunnel başlatılıyor...")
            subprocess.Popen(
                f"cloudflared tunnel --no-autoupdate run --token {token_row['value']}",
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
    except Exception as e:
        print(f"  [ERROR] Cloudflare auto-start hatası: {e}")
        
    conn.close()


if __name__ == "__main__":
    init_db()
    migrate_db()
    # Otomatik başlatma fonksiyonunu çağır
    auto_start_all()
    
    print(f"\n  +======================================+")
    print(f"  |     ArmPanel - Mobil Konsol          |")
    print(f"  |     http://localhost:{PANEL_PORT}            |")
    print(f"  +======================================+\n")
    app.run(host=PANEL_HOST, port=PANEL_PORT, debug=False, use_reloader=False)

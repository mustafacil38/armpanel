from flask import Flask, send_from_directory, session, jsonify, redirect
from config import SECRET_KEY, PANEL_HOST, PANEL_PORT
from database import init_db
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.services import services_bp
from routes.installer import installer_bp
from routes.settings import settings_bp
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
app.register_blueprint(installer_bp)
app.register_blueprint(settings_bp)


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


if __name__ == "__main__":
    init_db()
    print(f"\n  +======================================+")
    print(f"  |     ArmPanel - Mobil Konsol          |")
    print(f"  |     http://localhost:{PANEL_PORT}            |")
    print(f"  +======================================+\n")
    app.run(host=PANEL_HOST, port=PANEL_PORT, debug=True)

import sqlite3
import os
from werkzeug.security import generate_password_hash
from config import DATABASE_PATH, DEFAULT_USERNAME, DEFAULT_PASSWORD, DEFAULT_SERVICES


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            icon TEXT DEFAULT 'fa-solid fa-cube',
            description TEXT DEFAULT '',
            command_start TEXT DEFAULT '',
            command_stop TEXT DEFAULT '',
            command_restart TEXT DEFAULT '',
            process_name TEXT DEFAULT '',
            default_port INTEGER DEFAULT 0,
            config_files TEXT DEFAULT '',
            is_autostart INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS installed_apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            port TEXT DEFAULT '',
            status TEXT DEFAULT 'installed',
            installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed default user
    existing = cur.execute("SELECT id FROM users LIMIT 1").fetchone()
    if not existing:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (DEFAULT_USERNAME, generate_password_hash(DEFAULT_PASSWORD)),
        )

    # Seed default services
    for svc in DEFAULT_SERVICES:
        existing = cur.execute(
            "SELECT id FROM services WHERE name = ?", (svc["name"],)
        ).fetchone()
        if not existing:
            cur.execute(
                """INSERT INTO services
                   (name, icon, description, command_start, command_stop,
                    command_restart, process_name, default_port, config_files, is_autostart)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    svc["name"],
                    svc["icon"],
                    svc["description"],
                    svc["command_start"],
                    svc["command_stop"],
                    svc["command_restart"],
                    svc["process_name"],
                    svc["default_port"],
                    svc["config_files"],
                    0,
                ),
            )

    conn.commit()
    conn.close()


def migrate_db():
    """Migrate existing database to latest schema without data loss."""
    conn = get_db()
    cur = conn.cursor()

    tables = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = [t["name"] for t in tables]

    # Add installed_apps table
    if "installed_apps" not in table_names:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS installed_apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                port TEXT DEFAULT '',
                status TEXT DEFAULT 'installed',
                installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # Remove old container tables if they exist
    for tbl in ["containers", "container_env", "container_volumes"]:
        if tbl in table_names:
            cur.execute(f"DROP TABLE IF EXISTS {tbl}")

    # Add is_autostart column to services if missing
    if "services" in table_names:
        columns = cur.execute("PRAGMA table_info(services)").fetchall()
        col_names = [c["name"] for c in columns]
        if "is_autostart" not in col_names:
            cur.execute("ALTER TABLE services ADD COLUMN is_autostart INTEGER DEFAULT 0")

    conn.commit()
    conn.close()


# ── Installed Apps helpers ──

def save_installed_app(app_id, name, port="", status="installed"):
    conn = get_db()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO installed_apps (app_id, name, port, status, installed_at)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (app_id, name, port, status),
        )
        conn.commit()
    finally:
        conn.close()


def delete_installed_app(app_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM installed_apps WHERE app_id = ?", (app_id,))
        conn.commit()
    finally:
        conn.close()


def list_installed_apps():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM installed_apps ORDER BY installed_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

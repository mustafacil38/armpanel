import sqlite3
import os
from werkzeug.security import generate_password_hash
from config import DATABASE_PATH, DEFAULT_USERNAME, DEFAULT_PASSWORD, DEFAULT_SERVICES


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
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
                    command_restart, process_name, default_port, config_files)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                ),
            )

    conn.commit()
    conn.close()

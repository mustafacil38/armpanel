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
        CREATE TABLE IF NOT EXISTS containers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_id TEXT NOT NULL,
            name TEXT UNIQUE NOT NULL,
            image TEXT NOT NULL,
            port TEXT DEFAULT '',
            status TEXT DEFAULT 'installed',
            exec_mode TEXT DEFAULT 'P1',
            create_args TEXT DEFAULT '',
            compose_text TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS container_env (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            container_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT DEFAULT '',
            FOREIGN KEY (container_id) REFERENCES containers(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS container_volumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            container_id INTEGER NOT NULL,
            host_path TEXT NOT NULL,
            container_path TEXT NOT NULL,
            FOREIGN KEY (container_id) REFERENCES containers(id) ON DELETE CASCADE
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
    """Migrate existing database to latest schema without data loss.
    Safe to run on every startup."""
    conn = get_db()
    cur = conn.cursor()

    # Get existing tables
    tables = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = [t["name"] for t in tables]

    # Add containers table if missing
    if "containers" not in table_names:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS containers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT NOT NULL,
                name TEXT UNIQUE NOT NULL,
                image TEXT NOT NULL,
                port TEXT DEFAULT '',
                status TEXT DEFAULT 'installed',
                exec_mode TEXT DEFAULT 'P1',
                create_args TEXT DEFAULT '',
                compose_text TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # Add container_env table if missing
    if "container_env" not in table_names:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS container_env (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT DEFAULT '',
                FOREIGN KEY (container_id) REFERENCES containers(id) ON DELETE CASCADE
            )
        """)

    # Add container_volumes table if missing
    if "container_volumes" not in table_names:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS container_volumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_id INTEGER NOT NULL,
                host_path TEXT NOT NULL,
                container_path TEXT NOT NULL,
                FOREIGN KEY (container_id) REFERENCES containers(id) ON DELETE CASCADE
            )
        """)

    # Add is_autostart column to services if missing
    if "services" in table_names:
        columns = cur.execute("PRAGMA table_info(services)").fetchall()
        col_names = [c["name"] for c in columns]
        if "is_autostart" not in col_names:
            cur.execute("ALTER TABLE services ADD COLUMN is_autostart INTEGER DEFAULT 0")

    conn.commit()
    conn.close()


# ── Container DB helpers ──

def save_container(app_id, name, image, port="", exec_mode="P1",
                   create_args=None, compose_text="", env_vars=None, volumes=None):
    """Save a container record to the database."""
    conn = get_db()
    cur = conn.cursor()
    try:
        args_str = ",".join(create_args) if create_args else ""
        cur.execute(
            """INSERT OR REPLACE INTO containers
               (app_id, name, image, port, status, exec_mode, create_args, compose_text, updated_at)
               VALUES (?, ?, ?, ?, 'running', ?, ?, ?, CURRENT_TIMESTAMP)""",
            (app_id, name, image, port, exec_mode, args_str, compose_text),
        )
        container_id = cur.lastrowid

        # Save env vars
        if env_vars:
            cur.execute("DELETE FROM container_env WHERE container_id = ?", (container_id,))
            for k, v in env_vars.items():
                cur.execute(
                    "INSERT INTO container_env (container_id, key, value) VALUES (?, ?, ?)",
                    (container_id, k, str(v)),
                )

        # Save volumes
        if volumes:
            cur.execute("DELETE FROM container_volumes WHERE container_id = ?", (container_id,))
            for host_path, container_path in volumes:
                cur.execute(
                    "INSERT INTO container_volumes (container_id, host_path, container_path) VALUES (?, ?, ?)",
                    (container_id, host_path, container_path),
                )

        conn.commit()
        return container_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def update_container_status(name, status):
    """Update container status (running/stopped/installed)."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE containers SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
            (status, name),
        )
        conn.commit()
    finally:
        conn.close()


def get_container(name):
    """Get a container record by name."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM containers WHERE name = ?", (name,)).fetchone()
        if not row:
            return None
        container = dict(row)

        # Load env vars
        env_rows = conn.execute(
            "SELECT key, value FROM container_env WHERE container_id = ?",
            (container["id"],),
        ).fetchall()
        container["env"] = {r["key"]: r["value"] for r in env_rows}

        # Load volumes
        vol_rows = conn.execute(
            "SELECT host_path, container_path FROM container_volumes WHERE container_id = ?",
            (container["id"],),
        ).fetchall()
        container["volumes"] = [dict(v) for v in vol_rows]

        return container
    finally:
        conn.close()


def list_containers_db():
    """List all containers from database."""
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM containers ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_container_db(name):
    """Delete a container record from database."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM containers WHERE name = ?", (name,))
        conn.commit()
    finally:
        conn.close()

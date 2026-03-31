import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get("ARMPANEL_SECRET", "armpanel-secret-key-change-me")
DATABASE_PATH = os.path.join(BASE_DIR, "armpanel.db")
APPS_FILE = os.path.join(BASE_DIR, "apps.txt")

PANEL_HOST = "0.0.0.0"
PANEL_PORT = 1569
TTYD_PORT = 1570

GITHUB_REPO = "https://github.com/mustafacil38/armpanel"

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"

# Default service definitions
DEFAULT_SERVICES = [
    {
        "name": "Nginx",
        "icon": "fa-solid fa-server",
        "description": "High-performance web server",
        "command_start": "nginx",
        "command_stop": "nginx -s stop",
        "command_restart": "nginx -s reload",
        "process_name": "nginx",
        "default_port": 8080,
        "config_files": "/etc/nginx/nginx.conf,/etc/nginx/sites-available/default",
    },
    {
        "name": "ttyd",
        "icon": "fa-solid fa-terminal",
        "description": "Web-based terminal emulator",
        "command_start": f"/etc/ttyd/ttyd.aarch64 -p {TTYD_PORT} -W /bin/bash {os.path.join(BASE_DIR, 'term-wrapper.sh')} &",
        "command_stop": "pkill -f ttyd",
        "command_restart": f"pkill -f ttyd; sleep 1; /etc/ttyd/ttyd.aarch64 -p {TTYD_PORT} -W /bin/bash {os.path.join(BASE_DIR, 'term-wrapper.sh')} &",
        "process_name": "ttyd",
        "default_port": TTYD_PORT,
        "config_files": "",
    },
    {
        "name": "PHP-FPM",
        "icon": "fa-brands fa-php",
        "description": "PHP FastCGI Process Manager",
        "command_start": "php-fpm8.4",
        "command_stop": "pkill -f php-fpm",
        "command_restart": "pkill -f php-fpm; sleep 1; php-fpm8.4",
        "process_name": "php-fpm",
        "default_port": 9000,
        "config_files": "/etc/php/8.4/fpm/php.ini,/etc/php/8.4/fpm/pool.d/www.conf",
    },
    {
        "name": "File Browser",
        "icon": "fa-solid fa-folder-open",
        "description": "Web-based file manager",
        "command_start": "filebrowser -d /etc/filebrowser/filebrowser.db -a 0.0.0.0 -p 8083 -r / &",
        "command_stop": "pkill -f filebrowser",
        "command_restart": "pkill -f filebrowser; sleep 1; filebrowser -d /etc/filebrowser/filebrowser.db -a 0.0.0.0 -p 8083 -r / &",
        "process_name": "filebrowser",
        "default_port": 8083,
        "config_files": "",
    },
]

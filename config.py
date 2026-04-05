import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get("ARMPANEL_SECRET", "armpanel-secret-key-change-me")
DATABASE_PATH = os.path.join(BASE_DIR, "armpanel.db")


PANEL_HOST = "0.0.0.0"
PANEL_PORT = 1569
TTYD_PORT = 1570

GITHUB_REPO = "https://github.com/mustafacil38/armpanel"
APPSTORE_URL = "https://raw.githubusercontent.com/mustafacil38/armpanel/main/appstore.txt"

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"

DEFAULT_SERVICES = [
    {
        "name": "Nginx",
        "icon": "fa-solid fa-server",
        "description": "Web sunucusu (HTTP/HTTPS)",
        "command_start": "nginx",
        "command_stop": "nginx -s stop",
        "command_restart": "nginx -s reload",
        "process_name": "nginx",
        "default_port": 80,
        "config_files": "/etc/nginx/nginx.conf,/etc/nginx/sites-available/default",
    },
    {
        "name": "ttyd",
        "icon": "fa-solid fa-terminal",
        "description": "Web tabanlı terminal",
        "command_start": f"/usr/local/bin/ttyd -p {TTYD_PORT} -W tmux new -A -s armpanel &",
        "command_stop": "pkill -f ttyd",
        "command_restart": f"pkill -f ttyd; sleep 1; /usr/local/bin/ttyd -p {TTYD_PORT} -W tmux new -A -s armpanel &",
        "process_name": "ttyd",
        "default_port": TTYD_PORT,
        "config_files": "",
    },
    {
        "name": "PHP-FPM",
        "icon": "fa-brands fa-php",
        "description": "PHP FastCGI işlem yöneticisi",
        "command_start": "php-fpm8.2",
        "command_stop": "pkill -f php-fpm",
        "command_restart": "pkill -f php-fpm; sleep 1; php-fpm8.2",
        "process_name": "php-fpm",
        "default_port": 9000,
        "config_files": "/etc/php/8.2/fpm/php.ini,/etc/php/8.2/fpm/pool.d/www.conf",
    },
    {
        "name": "File Browser",
        "icon": "fa-solid fa-folder-open",
        "description": "Web tabanlı dosya yöneticisi",
        "command_start": "filebrowser -d /etc/filebrowser/filebrowser.db -a 0.0.0.0 -p 8083 -r / &",
        "command_stop": "pkill -f filebrowser",
        "command_restart": "pkill -f filebrowser; sleep 1; filebrowser -d /etc/filebrowser/filebrowser.db -a 0.0.0.0 -p 8083 -r / &",
        "process_name": "filebrowser",
        "default_port": 8083,
        "config_files": "",
    },
]

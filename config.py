import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get("ARMPANEL_SECRET", "armpanel-secret-key-change-me")
DATABASE_PATH = os.path.join(BASE_DIR, "armpanel.db")


PANEL_HOST = "0.0.0.0"
PANEL_PORT = 1569
TTYD_PORT = 1570

GITHUB_REPO = "https://github.com/mustafacil38/armpanel"

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
    {
        "name": "MariaDB",
        "icon": "fa-solid fa-database",
        "description": "MariaDB Veritabanı Sunucusu",
        "command_start": "mariadbd-safe &",
        "command_stop": "pkill -f mariadbd",
        "command_restart": "pkill -f mariadbd; sleep 1; mariadbd-safe &",
        "process_name": "mariadbd",
        "default_port": 3306,
        "config_files": "/etc/mysql/mariadb.conf.d/50-server.cnf",
    },
    {
        "name": "phpMyAdmin",
        "icon": "fa-brands fa-php",
        "description": "Web tabanlı MySQL veritabanı yönetimi",
        "command_start": "",
        "command_stop": "",
        "command_restart": "",
        "process_name": "php-fpm",
        "default_port": 8084,
        "config_files": "/etc/nginx/sites-available/phpmyadmin",
    },
    {
        "name": "Nextcloud",
        "icon": "fa-solid fa-cloud",
        "description": "Kişisel bulut depolama platformu",
        "command_start": "",
        "command_stop": "",
        "command_restart": "",
        "process_name": "php-fpm",
        "default_port": 8081,
        "config_files": "/etc/nginx/sites-available/nextcloud",
    },
    {
        "name": "AdGuard Home",
        "icon": "fa-solid fa-shield",
        "description": "Ağ bazlı reklam engelleyici",
        "command_start": "/opt/AdGuardHome/AdGuardHome -w /opt/AdGuardHome/work -c /opt/AdGuardHome/AdGuardHome.yaml &",
        "command_stop": "pkill -f AdGuardHome",
        "command_restart": "pkill -f AdGuardHome; sleep 1; /opt/AdGuardHome/AdGuardHome -w /opt/AdGuardHome/work -c /opt/AdGuardHome/AdGuardHome.yaml &",
        "process_name": "AdGuardHome",
        "default_port": 3000,
        "config_files": "/opt/AdGuardHome/AdGuardHome.yaml",
    },
    {
        "name": "Ghost",
        "icon": "fa-solid fa-ghost",
        "description": "Ghost Blog platformu",
        "command_start": "sudo -i -u ghostuser bash -c 'cd /var/www/ghost && ghost start' || true",
        "command_stop": "sudo -i -u ghostuser bash -c 'cd /var/www/ghost && ghost stop' || true",
        "command_restart": "sudo -i -u ghostuser bash -c 'cd /var/www/ghost && ghost restart' || true",
        "process_name": "ghost",
        "default_port": 2368,
        "config_files": "/var/www/ghost/config.development.json",
    },
    {
        "name": "WireGuard VPN",
        "icon": "fa-solid fa-network-wired",
        "description": "WireGuard Sunucusu ve Web Paneli",
        "command_start": "nohup /usr/local/bin/start-wireguard-ui > /dev/null 2>&1 &",
        "command_stop": "pkill -f wireguard-ui; wg-quick down wg0 2>/dev/null || true",
        "command_restart": "pkill -f wireguard-ui; wg-quick down wg0 2>/dev/null || true; sleep 2; nohup /usr/local/bin/start-wireguard-ui > /dev/null 2>&1 &",
        "process_name": "wireguard-ui",
        "default_port": 5000,
        "config_files": "/etc/wireguard/wg0.conf"
    },
    {
        "name": "Samba Sunucusu",
        "icon": "fa-solid fa-hard-drive",
        "description": "Yerel Ag Dosya Paylasimi (SanalDisk)",
        "command_start": "/usr/local/bin/start-samba",
        "command_stop": "pkill -f smbd",
        "command_restart": "pkill -f smbd; sleep 1; /usr/local/bin/start-samba",
        "process_name": "smbd",
        "default_port": 445,
        "config_files": "/etc/samba/smb.conf"
    }
]

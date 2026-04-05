#!/bin/bash
# ============================================================
# ArmPanel - Kurulum Betiği
# Ortam: Termux > proot-distro (Debian 13/Trixie) > root
# NOT: Cihaz ROOTLU DEĞIL (bootloader kilitli). Proot ile çalışır.
# ============================================================

if [ ! -d /dev/shm ]; then
    mkdir -p /dev/shm 2>/dev/null || true
    mount -t tmpfs tmpfs /dev/shm 2>/dev/null || true
fi

echo ""
echo "=========================================="
echo "  ArmPanel Kurulum Betigi"
echo "  Ortam: Debian 13 (Proot)"
echo "=========================================="
echo ""

ARCH=$(uname -m)
echo "[0] Mimari: $ARCH"
echo ""

# ── dpkg onarımı ──
echo "[1] dpkg onariliyor..."
dpkg --configure -a
apt --fix-broken install -y
echo ""

# ── Temel araçlar ──
echo "[2] Temel sistem araclari kuruluyor..."
apt update
apt install -y curl wget git unzip zip tar apt-transport-https ca-certificates gnupg procps sudo cron logrotate net-tools iproute2 htop tree ncdu jq nano less
echo ""

# ── Python 3 ──
echo "[3] Python 3 ve pip kuruluyor..."
apt install -y python3 python3-pip python3-venv python3-dev python3-full
echo ""

# ── Nginx ──
echo "[4] Nginx kuruluyor..."
apt install -y nginx
echo ""

# ── PHP 8.4 FPM ──
echo "[5] PHP 8.4 FPM kuruluyor..."
apt install -y php8.4-fpm php8.4-cli php8.4-common php8.4-mysql php8.4-pgsql php8.4-sqlite3 php8.4-curl php8.4-xml php8.4-mbstring php8.4-zip php8.4-gd php8.4-intl php8.4-opcache php8.4-readline
echo ""

# php-fpm socket -> port
if [ -f /etc/php/8.4/fpm/pool.d/www.conf ]; then
    sed -i 's|^listen = /run.*|listen = 127.0.0.1:9000|' /etc/php/8.4/fpm/pool.d/www.conf
fi
echo ""

# ── ttyd ──
echo "[6] ttyd kuruluyor..."
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    TTYD_ARCH="aarch64"
else
    TTYD_ARCH="x86_64"
fi
wget "https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.${TTYD_ARCH}" -O /usr/local/bin/ttyd
chmod +x /usr/local/bin/ttyd
echo ""

# ── tmux ──
echo "[7] tmux kuruluyor..."
apt install -y tmux
echo ""

# ── File Browser ──
echo "[8] File Browser kuruluyor..."
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    FB_ARCH="arm64"
else
    FB_ARCH="amd64"
fi
wget "https://github.com/filebrowser/filebrowser/releases/download/v2.32.0/linux-${FB_ARCH}-filebrowser.tar.gz" -O /tmp/filebrowser.tar.gz
tar xzf /tmp/filebrowser.tar.gz -C /tmp
mv /tmp/filebrowser /usr/local/bin/filebrowser
chmod +x /usr/local/bin/filebrowser
rm -f /tmp/filebrowser.tar.gz
echo ""

# ── Node.js ──
echo "[9] Node.js kuruluyor..."
apt install -y nodejs npm
echo ""

# ── AdGuard Home ──
echo "[10] AdGuard Home kuruluyor..."
mkdir -p /opt/adguardhome
AGH_VER=$(curl -s https://api.github.com/repos/AdguardTeam/AdGuardHome/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d v)
wget "https://github.com/AdguardTeam/AdGuardHome/releases/download/v${AGH_VER}/AdGuardHome_linux_arm64.tar.gz" -O /tmp/adguardhome.tar.gz
tar xzf /tmp/adguardhome.tar.gz -C /tmp
mv /tmp/AdGuardHome/AdGuardHome /opt/adguardhome/AdGuardHome
chmod +x /opt/adguardhome/AdGuardHome
rm -rf /tmp/AdGuardHome /tmp/adguardhome.tar.gz
echo "  -> AdGuard Home v${AGH_VER} kuruldu"
echo ""

# ── Nextcloud ──
echo "[11] Nextcloud kuruluyor..."
mkdir -p /var/www/nextcloud
mkdir -p /var/www/nextcloud/data
wget "https://download.nextcloud.com/server/releases/latest.zip" -O /tmp/nextcloud.zip
unzip /tmp/nextcloud.zip -d /tmp
cp -r /tmp/nextcloud/* /var/www/nextcloud/
chown -R www-data:www-data /var/www/nextcloud
rm -rf /tmp/nextcloud /tmp/nextcloud.zip

# PHP ayarlari - Nextcloud icin
cat > /etc/php/8.4/fpm/conf.d/99-nextcloud.ini << 'PHPCONF'
upload_max_filesize = 512M
post_max_size = 512M
memory_limit = 512M
max_execution_time = 3600
output_buffering = off
PHPCONF

# Nextcloud nginx config (port 8081)
cat > /etc/nginx/sites-available/nextcloud << 'NCCONF'
server {
    listen 8081;
    server_name _;
    root /var/www/nextcloud;
    index index.php;
    client_max_body_size 512M;

    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy no-referrer;

    location = /.well-known/carddav { return 301 /remote.php/dav/; }
    location = /.well-known/caldav  { return 301 /remote.php/dav/; }

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ ^/(?:build|tests|config|lib|3rdparty|templates|data)/ {
        deny all;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass 127.0.0.1:9000;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param PATH_INFO $fastcgi_path_info;
    }
}
NCCONF
ln -sf /etc/nginx/sites-available/nextcloud /etc/nginx/sites-enabled/nextcloud
echo ""

# ── n8n ──
echo "[12] n8n kuruluyor..."
npm install -g n8n
echo ""

# ── Ghost ──
echo "[13] Ghost kuruluyor..."
mkdir -p /var/www/ghost
npm install -g ghost-cli
cd /var/www/ghost
ghost install local --no-setup-linux-user --no-start
cd /root
echo ""

# ── MariaDB ──
echo "[14] MariaDB kuruluyor..."
apt install -y mariadb-server mariadb-client
mkdir -p /run/mysqld
chown mysql:mysql /run/mysqld
mysql_install_db --user=mysql --datadir=/var/lib/mysql
echo ""

# ── phpMyAdmin ──
echo "[15] phpMyAdmin kuruluyor..."
PMA_VER=$(curl -s https://api.github.com/repos/phpmyadmin/phpmyadmin/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d v)
wget "https://files.phpmyadmin.net/phpMyAdmin/${PMA_VER}/phpMyAdmin-${PMA_VER}-all-languages.zip" -O /tmp/pma.zip
mkdir -p /var/www/html/phpmyadmin
unzip /tmp/pma.zip -d /tmp
cp -r /tmp/phpMyAdmin-${PMA_VER}-all-languages/* /var/www/html/phpmyadmin/
cp /var/www/html/phpmyadmin/config.sample.inc.php /var/www/html/phpmyadmin/config.inc.php
rm -rf /tmp/pma.zip /tmp/phpMyAdmin-*
echo ""

# ── Jellyfin ──
echo "[16] Jellyfin kuruluyor..."
apt install -y jellyfin
mkdir -p /etc/jellyfin /var/cache/jellyfin
echo ""

# ── Vaultwarden ──
echo "[17] Vaultwarden kuruluyor..."
mkdir -p /opt/vaultwarden
VW_VER=$(curl -s https://api.github.com/repos/dani-garcia/vaultwarden/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d v)
wget "https://github.com/dani-garcia/vaultwarden/releases/download/${VW_VER}/vaultwarden-${VW_VER}-aarch64-unknown-linux-musl.tar.gz" -O /tmp/vw.tar.gz
tar xzf /tmp/vw.tar.gz -C /tmp
mv /tmp/vaultwarden /opt/vaultwarden/vaultwarden
chmod +x /opt/vaultwarden/vaultwarden
rm -f /tmp/vw.tar.gz
echo "  -> Vaultwarden ${VW_VER} kuruldu"
echo ""

# ── Uptime Kuma ──
echo "[18] Uptime Kuma kuruluyor..."
mkdir -p /opt/uptime-kuma
UK_VER=$(curl -s https://api.github.com/repos/louislam/uptime-kuma/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d v)
wget "https://github.com/louislam/uptime-kuma/releases/download/${UK_VER}/uptime-kuma-${UK_VER}.tar.gz" -O /tmp/uk.tar.gz
tar xzf /tmp/uk.tar.gz -C /opt/uptime-kuma
cd /opt/uptime-kuma
npm install --production
cd /root
rm -f /tmp/uk.tar.gz
echo "  -> Uptime Kuma ${UK_VER} kuruldu"
echo ""

# ── rclone ──
echo "[19] rclone kuruluyor..."
curl -sSf https://rclone.org/install.sh | bash
echo ""

# ── Syncthing ──
echo "[20] Syncthing kuruluyor..."
apt install -y syncthing
echo ""

# ── Samba ──
echo "[21] Samba kuruluyor..."
apt install -y samba

# Rootsuz cihaz icin yuksek port ayari (4455)
cat > /etc/samba/smb.conf << 'SMBCONF'
[global]
   workgroup = WORKGROUP
   server string = ArmPanel Samba
   smb ports = 4455
   map to guest = bad user
   dns proxy = no

[shared]
   path = /root/shared
   browseable = yes
   writable = yes
   guest ok = yes
   read only = no
   create mask = 0755
   directory mask = 0755
SMBCONF

mkdir -p /root/shared
chmod 755 /root/shared
echo ""

# ═══════════════════════════════════════════════════════════
#  NGINX ANA CONFIG
# ═══════════════════════════════════════════════════════════
echo "[22] Nginx yapilandirmasi..."

cat > /etc/nginx/sites-available/default << 'NGINXCONF'
server {
    listen 8080 default_server;
    listen [::]:8080 default_server;
    root /var/www/html;
    index index.php index.html index.htm;
    server_name _;
    location / { try_files $uri $uri/ =404; }
    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass 127.0.0.1:9000;
    }
}
NGINXCONF

echo ""

# ═══════════════════════════════════════════════════════════
#  ARMPANEL PROJESI
# ═══════════════════════════════════════════════════════════
echo "[23] ArmPanel projesi kuruluyor..."

INSTALL_DIR="/root/armpanel"
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR"
    git pull origin main
else
    git clone https://github.com/mustafacil38/armpanel.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

pip3 install -r requirements.txt --break-system-packages
echo ""

# ═══════════════════════════════════════════════════════════
#  BAŞLATMA BETİĞİ
# ═══════════════════════════════════════════════════════════
echo "[24] Baslatma betigi olusturuluyor..."

cat > /usr/local/bin/start-armpanel << 'STARTSCRIPT'
#!/bin/bash
nginx
php-fpm8.4
pkill -f "ttyd.*1570"
/usr/local/bin/ttyd -p 1570 -W tmux new -A -s armpanel &
pkill -f "filebrowser"
filebrowser -d /etc/filebrowser/filebrowser.db -a 0.0.0.0 -p 8083 -r / &
cd /root/armpanel
python3 app.py
STARTSCRIPT

chmod +x /usr/local/bin/start-armpanel

echo ""
echo "=========================================="
echo "  Kurulum Tamamlandi!"
echo "=========================================="
echo ""
echo "  Panel:       http://localhost:1569"
echo "  ttyd:        http://localhost:1570"
echo "  Nginx:       http://localhost:8080"
echo "  AdGuard:     http://localhost:3000"
echo "  Nextcloud:   http://localhost:8081"
echo "  n8n:         http://localhost:5678"
echo "  Ghost:       http://localhost:2368"
echo "  MariaDB:     localhost:3306"
echo "  phpMyAdmin:  http://localhost:8080/phpmyadmin"
echo "  Jellyfin:    http://localhost:8096"
echo "  Vaultwarden: http://localhost:8085"
echo "  UptimeKuma:  http://localhost:3001"
echo "  Syncthing:   http://localhost:8384"
echo "  Samba:       smb://localhost:4455"
echo ""
echo "  Kullanici: admin / admin"
echo "  Baslat: python3 /root/armpanel/app.py"
echo ""
echo "=========================================="
echo ""

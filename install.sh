#!/bin/bash
# ============================================================
# ArmPanel - Kurulum Betiği
# Ortam: Rootlu ARM64 cihaz (Debian 12/Bookworm)
# GEREKSINIM: Root erişimi (80, 443, 445 gibi düşük portlar için)
# NOT: Diğer uygulamalar Panel > Mağaza sayfasından kurulur.
# ============================================================

echo ""
echo "=========================================="
echo "  ArmPanel Kurulum Betigi"
echo "  Ortam: Debian 12 (Rootlu ARM64)"
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

cat > /etc/nginx/sites-available/default << 'NGINXCONF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
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

# ── PHP 8.2 FPM ──
echo "[5] PHP 8.2 FPM kuruluyor..."
apt install -y php8.2-fpm php8.2-cli php8.2-common php8.2-mysql php8.2-pgsql php8.2-sqlite3 php8.2-curl php8.2-xml php8.2-mbstring php8.2-zip php8.2-gd php8.2-intl php8.2-opcache php8.2-readline

if [ -f /etc/php/8.2/fpm/pool.d/www.conf ]; then
    sed -i 's|^listen = /run.*|listen = 127.0.0.1:9000|' /etc/php/8.2/fpm/pool.d/www.conf
fi

PHPINI="/etc/php/8.2/fpm/php.ini"
if [ -f "$PHPINI" ]; then
    sed -i 's/^upload_max_filesize.*/upload_max_filesize = 512M/' "$PHPINI"
    sed -i 's/^post_max_size.*/post_max_size = 512M/' "$PHPINI"
    sed -i 's/^memory_limit.*/memory_limit = 512M/' "$PHPINI"
    sed -i 's/^max_execution_time.*/max_execution_time = 3600/' "$PHPINI"
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

# ── MariaDB ──
echo "[9] MariaDB kuruluyor..."
apt install -y mariadb-server
sed -i "s/127.0.0.1/0.0.0.0/" /etc/mysql/mariadb.conf.d/50-server.cnf
mariadbd-safe &
sleep 5
mariadb -e "CREATE USER IF NOT EXISTS 'admin'@'%' IDENTIFIED BY '123456'; GRANT ALL PRIVILEGES ON *.* TO 'admin'@'%' WITH GRANT OPTION; FLUSH PRIVILEGES;"
echo ""

# ── phpMyAdmin ──
echo "[10] phpMyAdmin kuruluyor..."
wget -q "https://www.phpmyadmin.net/downloads/phpMyAdmin-latest-all-languages.tar.gz" -O /tmp/pma.tar.gz
mkdir -p /var/www/phpmyadmin
tar xzf /tmp/pma.tar.gz -C /var/www/phpmyadmin --strip-components=1
chown -R www-data:www-data /var/www/phpmyadmin
cat > /etc/nginx/sites-available/phpmyadmin << 'EOF'
server {
    listen 8084;
    server_name _;
    root /var/www/phpmyadmin;
    index index.php index.html index.htm;
    location / { try_files $uri $uri/ =404; }
    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass 127.0.0.1:9000;
    }
}
EOF
ln -sf /etc/nginx/sites-available/phpmyadmin /etc/nginx/sites-enabled/phpmyadmin
rm -f /tmp/pma.tar.gz
echo ""

# ── Nextcloud ──
echo "[11] Nextcloud kuruluyor..."
wget -q "https://download.nextcloud.com/server/releases/latest.zip" -O /tmp/next.zip
unzip -q /tmp/next.zip -d /var/www/
chown -R www-data:www-data /var/www/nextcloud
cat > /etc/nginx/sites-available/nextcloud << 'EOF'
server {
    listen 8081;
    server_name _;
    root /var/www/nextcloud;
    include /etc/nginx/mime.types;
    types { application/javascript mjs; }
    location / { rewrite ^ /index.php; }
    location ~ ^\/(?:index|remote|public|cron|core\/ajax\/update|status|ocs\/v[12]|updater\/.+|ocm-provider\/.+)\.php(?:$|\/) {
        fastcgi_split_path_info ^(.+?\.php)(\/.*|)$;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_pass 127.0.0.1:9000;
    }
    location ~ \.(?:css|js|mjs|woff2?|svg|gif|png|html|ttf|ico|jpg|jpeg)$ { try_files $uri /index.php$request_uri; }
}
EOF
ln -sf /etc/nginx/sites-available/nextcloud /etc/nginx/sites-enabled/nextcloud
rm -f /tmp/next.zip
echo ""

# ── AdGuard Home ──
echo "[12] AdGuard Home kuruluyor..."
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then ADG_ARCH="arm64"; else ADG_ARCH="amd64"; fi
wget -q "https://static.adguard.com/adguardhome/release/AdGuardHome_linux_${ADG_ARCH}.tar.gz" -O /tmp/adg.tar.gz
tar xzf /tmp/adg.tar.gz -C /opt
rm -f /tmp/adg.tar.gz
echo ""

# ── Node.js ve Ghost ──
echo "[13] Ghost kuruluyor..."
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs
npm install ghost-cli@latest -g
useradd -m -s /bin/bash ghostuser || true
mkdir -p /var/www/ghost
chown -R ghostuser:ghostuser /var/www/ghost
mariadb -e "CREATE DATABASE IF NOT EXISTS ghost_db;" || true
su - ghostuser -c "cd /var/www/ghost && ghost install local --db sqlite3 --no-prompt" || true
echo ""

# ═══════════════════════════════════════════════════════════
#  ARMPANEL PROJESI
# ═══════════════════════════════════════════════════════════
echo "[14] ArmPanel projesi kuruluyor..."

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
echo "[15] Baslatma betigi olusturuluyor..."

cat > /usr/local/bin/start-armpanel << 'STARTSCRIPT'
#!/bin/bash
nginx
php-fpm8.2
pkill -f "ttyd.*1570"
/usr/local/bin/ttyd -p 1570 -W tmux new -A -s armpanel &
pkill -f "filebrowser"
filebrowser -d /etc/filebrowser/filebrowser.db -a 0.0.0.0 -p 8083 -r / &
mariadbd-safe &
/opt/AdGuardHome/AdGuardHome -w /opt/AdGuardHome/work -c /opt/AdGuardHome/AdGuardHome.yaml &
su - ghostuser -c "cd /var/www/ghost && ghost start" &
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
echo "  Nginx:       http://localhost:80"
echo "  FileBrowser: http://localhost:8083"
echo ""
echo "  Kullanici: admin / admin"
echo "  Baslat: python3 /root/armpanel/app.py"
echo ""
echo "  Diger uygulamalar: Panel > Magaza sayfasindan kurun!"
echo ""
echo "=========================================="
echo ""

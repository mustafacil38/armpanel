#!/bin/bash
# ============================================================
# ArmPanel - Kurulum Betiği
# Ortam: Termux > proot-distro (Debian 13/Trixie) > root
# NOT: Cihaz ROOTLU DEĞIL (bootloader kilitli). Proot ile çalışır.
# ============================================================

# set -e KALDIRILDI - bazı paketler Debian 13'te mevcut değil, betik devam etsin

echo ""
echo "  +==========================================+"
echo "  |     ArmPanel Kurulum Betiği              |"
echo "  |     Ortam: Debian 13 (Proot)             |"
echo "  +==========================================+"
echo ""

# ── 0. Mimari tespiti ──
ARCH=$(uname -m)
echo "[0/16] Mimari tespit ediliyor: $ARCH"

if [ "$ARCH" != "aarch64" ] && [ "$ARCH" != "arm64" ]; then
    echo "UYARI: Bu betik ARM64 için tasarlanmıştır. Mevcut: $ARCH"
fi

# ── 1. Temel sistem araçları ──
echo "[1/16] Temel sistem araçları kuruluyor..."
apt update -y
apt install -y curl wget git unzip zip tar \
    apt-transport-https ca-certificates gnupg procps \
    sudo cron logrotate net-tools iproute2 \
    htop tree ncdu jq nano less 2>/dev/null || true

for pkg in software-properties-common lsb-release build-essential pkg-config; do
    apt install -y "$pkg" 2>/dev/null || echo "  -> $pkg bulunamadı, atlanıyor"
done

# ── 2. Python 3 + pip ──
echo "[2/16] Python 3 ve pip kuruluyor..."
apt install -y python3 python3-pip python3-venv python3-dev python3-full

# ── 3. Nginx ──
echo "[3/16] Nginx kuruluyor..."
apt install -y nginx

# ── 4. PHP 8.4 FPM ──
echo "[4/16] PHP 8.4 FPM kuruluyor..."
if ! apt-cache show php8.4-fpm &>/dev/null; then
    echo "  -> PHP 8.4 resmi depoda bulunamadı, Sury deposu ekleniyor..."
    curl -sSLo /usr/share/keyrings/deb.sury.org-php.gpg https://packages.sury.org/php/apt.gpg
    echo "deb [signed-by=/usr/share/keyrings/deb.sury.org-php.gpg] https://packages.sury.org/php/ $(lsb_release -sc) main" > /etc/apt/sources.list.d/php.list
    apt update -y
fi

apt install -y php8.4-fpm php8.4-cli php8.4-common php8.4-mysql \
    php8.4-pgsql php8.4-sqlite3 php8.4-curl php8.4-xml php8.4-mbstring \
    php8.4-zip php8.4-gd php8.4-intl php8.4-opcache php8.4-readline

# php-fpm socket -> port
if [ -f /etc/php/8.4/fpm/pool.d/www.conf ]; then
    sed -i 's|^listen = /run.*|listen = 127.0.0.1:9000|' /etc/php/8.4/fpm/pool.d/www.conf 2>/dev/null || true
fi

# ── 5. ttyd (Web Terminal) ──
echo "[5/16] ttyd kuruluyor..."
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    TTYD_ARCH="aarch64"
else
    TTYD_ARCH="x86_64"
fi
wget -q "https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.${TTYD_ARCH}" -O /usr/local/bin/ttyd
chmod +x /usr/local/bin/ttyd

# ── 6. tmux ──
echo "[6/16] tmux kuruluyor..."
apt install -y tmux

# ── 7. File Browser ──
echo "[7/16] File Browser kuruluyor..."
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    FB_ARCH="arm64"
else
    FB_ARCH="amd64"
fi
wget -q "https://github.com/filebrowser/filebrowser/releases/download/v2.32.0/linux-${FB_ARCH}-filebrowser.tar.gz" -O /tmp/filebrowser.tar.gz
tar xzf /tmp/filebrowser.tar.gz -C /tmp
mv /tmp/filebrowser /usr/local/bin/filebrowser
chmod +x /usr/local/bin/filebrowser
rm -f /tmp/filebrowser.tar.gz

# ── 8. Node.js + npm ──
echo "[8/16] Node.js kuruluyor..."
apt install -y nodejs npm 2>/dev/null || true

# ═══════════════════════════════════════════════════════════
#  UYGULAMALAR
# ═══════════════════════════════════════════════════════════

# ── 9. AdGuard Home ──
echo "[9/16] AdGuard Home kuruluyor..."
mkdir -p /opt/adguardhome
AGH_VER=$(curl -s https://api.github.com/repos/AdguardTeam/AdGuardHome/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d v)
wget -q "https://github.com/AdguardTeam/AdGuardHome/releases/download/v${AGH_VER}/AdGuardHome_linux_${ARCH}.tar.gz" -O /tmp/adguardhome.tar.gz 2>/dev/null || \
wget -q "https://github.com/AdguardTeam/AdGuardHome/releases/download/v${AGH_VER}/AdGuardHome_linux_arm64.tar.gz" -O /tmp/adguardhome.tar.gz 2>/dev/null || true
if [ -f /tmp/adguardhome.tar.gz ]; then
    tar xzf /tmp/adguardhome.tar.gz -C /tmp
    mv /tmp/AdGuardHome/AdGuardHome /opt/adguardhome/AdGuardHome 2>/dev/null || true
    chmod +x /opt/adguardhome/AdGuardHome
    rm -rf /tmp/AdGuardHome /tmp/adguardhome.tar.gz
    echo "  -> AdGuard Home v${AGH_VER} kuruldu"
fi

# ── 10. Nextcloud ──
echo "[10/16] Nextcloud kuruluyor..."
mkdir -p /var/www/nextcloud
NC_VER=$(curl -s https://api.github.com/repos/nextcloud/server/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d v)
wget -q "https://download.nextcloud.com/server/releases/nextcloud-${NC_VER}.zip" -O /tmp/nextcloud.zip 2>/dev/null || \
wget -q "https://download.nextcloud.com/server/releases/latest.zip" -O /tmp/nextcloud.zip 2>/dev/null || true
if [ -f /tmp/nextcloud.zip ]; then
    unzip -q /tmp/nextcloud.zip -d /tmp 2>/dev/null
    cp -r /tmp/nextcloud/* /var/www/nextcloud/ 2>/dev/null || true
    chown -R www-data:www-data /var/www/nextcloud 2>/dev/null || true
    rm -rf /tmp/nextcloud /tmp/nextcloud.zip
    echo "  -> Nextcloud kuruldu"
fi

# Nextcloud nginx config
cat > /etc/nginx/sites-available/nextcloud << 'NCCONF'
server {
    listen 8080;
    server_name _;
    root /var/www/nextcloud;
    index index.php;
    client_max_body_size 512M;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass 127.0.0.1:9000;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }
}
NCCONF
ln -sf /etc/nginx/sites-available/nextcloud /etc/nginx/sites-enabled/nextcloud 2>/dev/null || true

# ── 11. n8n ──
echo "[11/16] n8n kuruluyor..."
npm install -g n8n 2>/dev/null && echo "  -> n8n kuruldu" || echo "  -> n8n kurulumu başarısız"

# ── 12. Ghost ──
echo "[12/16] Ghost kuruluyor..."
mkdir -p /var/www/ghost
npm install -g ghost-cli 2>/dev/null || true
cd /var/www/ghost && ghost install local --no-setup-linux-user --no-start 2>/dev/null || echo "  -> Ghost kurulumu manuel yapılacak"
cd /root

# ── 13. MariaDB ──
echo "[13/16] MariaDB kuruluyor..."
apt install -y mariadb-server mariadb-client 2>/dev/null || true
mkdir -p /run/mysqld && chown mysql:mysql /run/mysqld 2>/dev/null || true
echo "  -> MariaDB kuruldu (mysqld_safe ile başlatılır)"

# ── 14. phpMyAdmin ──
echo "[14/16] phpMyAdmin kuruluyor..."
PMA_VER=$(curl -s https://api.github.com/repos/phpmyadmin/phpmyadmin/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d v)
wget -q "https://files.phpmyadmin.net/phpMyAdmin/${PMA_VER}/phpMyAdmin-${PMA_VER}-all-languages.zip" -O /tmp/pma.zip 2>/dev/null || true
if [ -f /tmp/pma.zip ]; then
    mkdir -p /var/www/html/phpmyadmin
    unzip -q /tmp/pma.zip -d /tmp 2>/dev/null
    cp -r /tmp/phpMyAdmin-${PMA_VER}-all-languages/* /var/www/html/phpmyadmin/ 2>/dev/null || true
    rm -rf /tmp/pma.zip /tmp/phpMyAdmin-*
    echo "  -> phpMyAdmin kuruldu"
fi

# ── 15. Jellyfin ──
echo "[15/16] Jellyfin kuruluyor..."
apt install -y jellyfin 2>/dev/null || {
    # Manuel kurulum
    JF_VER=$(curl -s https://api.github.com/repos/jellyfin/jellyfin/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d v)
    wget -q "https://repo.jellyfin.org/files/server/linux/stable/debian/arm64/${JF_VER}/jellyfin_${JF_VER}_arm64.deb" -O /tmp/jellyfin.deb 2>/dev/null || true
    if [ -f /tmp/jellyfin.deb ]; then
        apt install -y /tmp/jellyfin.deb 2>/dev/null || dpkg -i /tmp/jellyfin.deb 2>/dev/null || true
        rm -f /tmp/jellyfin.deb
    fi
}
mkdir -p /etc/jellyfin /var/cache/jellyfin
echo "  -> Jellyfin kuruldu"

# ── 16. WireGuard ──
echo "[16/16] WireGuard kuruluyor..."
apt install -y wireguard 2>/dev/null || echo "  -> WireGuard kurulamadı (kernel modülü gerekebilir)"

# ── 17. Vaultwarden (Bitwarden) ──
echo "[17/16] Vaultwarden kuruluyor..."
mkdir -p /opt/vaultwarden
VW_VER=$(curl -s https://api.github.com/repos/dani-garcia/vaultwarden/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d v)
wget -q "https://github.com/dani-garcia/vaultwarden/releases/download/${VW_VER}/vaultwarden-${VW_VER}-aarch64-unknown-linux-musl.tar.gz" -O /tmp/vw.tar.gz 2>/dev/null || \
wget -q "https://github.com/dani-garcia/vaultwarden/releases/download/${VW_VER}/vaultwarden-${VW_VER}-armv7-unknown-linux-musleabihf.tar.gz" -O /tmp/vw.tar.gz 2>/dev/null || true
if [ -f /tmp/vw.tar.gz ]; then
    tar xzf /tmp/vw.tar.gz -C /tmp 2>/dev/null
    mv /tmp/vaultwarden /opt/vaultwarden/vaultwarden 2>/dev/null || true
    chmod +x /opt/vaultwarden/vaultwarden
    rm -f /tmp/vw.tar.gz
    echo "  -> Vaultwarden ${VW_VER} kuruldu"
fi

# ── 18. Uptime Kuma ──
echo "[18/16] Uptime Kuma kuruluyor..."
mkdir -p /opt/uptime-kuma
UK_VER=$(curl -s https://api.github.com/repos/louislam/uptime-kuma/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d v)
wget -q "https://github.com/louislam/uptime-kuma/releases/download/${UK_VER}/uptime-kuma-${UK_VER}.tar.gz" -O /tmp/uk.tar.gz 2>/dev/null || true
if [ -f /tmp/uk.tar.gz ]; then
    tar xzf /tmp/uk.tar.gz -C /opt/uptime-kuma 2>/dev/null
    cd /opt/uptime-kuma && npm install --production 2>/dev/null || true
    rm -f /tmp/uk.tar.gz
    echo "  -> Uptime Kuma ${UK_VER} kuruldu"
fi

# ── 19. rclone ──
echo "[19/16] rclone kuruluyor..."
curl -sSf https://rclone.org/install.sh | bash 2>/dev/null && echo "  -> rclone kuruldu" || echo "  -> rclone kurulumu başarısız"

# ── 20. Syncthing ──
echo "[20/16] Syncthing kuruluyor..."
apt install -y syncthing 2>/dev/null || {
    ST_VER=$(curl -s https://api.github.com/repos/syncthing/syncthing/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d v)
    wget -q "https://github.com/syncthing/syncthing/releases/download/${ST_VER}/syncthing-linux-${ARCH}-${ST_VER}.tar.gz" -O /tmp/st.tar.gz 2>/dev/null || true
    if [ -f /tmp/st.tar.gz ]; then
        tar xzf /tmp/st.tar.gz -C /tmp 2>/dev/null
        mv /tmp/syncthing-*/syncthing /usr/local/bin/syncthing 2>/dev/null || true
        chmod +x /usr/local/bin/syncthing
        rm -rf /tmp/st.tar.gz /tmp/syncthing-*
        echo "  -> Syncthing ${ST_VER} kuruldu"
    fi
}

# ── 21. Samba ──
echo "[21/16] Samba kuruluyor..."
apt install -y samba 2>/dev/null && echo "  -> Samba kuruldu" || echo "  -> Samba kurulumu başarısız"

# ═══════════════════════════════════════════════════════════
#  NGINX ANA CONFIG
# ═══════════════════════════════════════════════════════════
cat > /etc/nginx/sites-available/default << 'NGINXCONF'
server {
    listen 8080 default_server;
    listen [::]:8080 default_server;

    root /var/www/html;
    index index.php index.html index.htm;
    server_name _;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass 127.0.0.1:9000;
    }
}
NGINXCONF

# ═══════════════════════════════════════════════════════════
#  ARMPANEL PROJESI
# ═══════════════════════════════════════════════════════════
echo ""
echo "  -> ArmPanel projesi kuruluyor..."

INSTALL_DIR="/root/armpanel"
if [ -d "$INSTALL_DIR" ]; then
    echo "  -> Mevcut kurulum bulundu, güncelleniyor..."
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    git clone https://github.com/mustafacil38/armpanel.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

pip3 install -r requirements.txt --break-system-packages

# ═══════════════════════════════════════════════════════════
#  BASLATMA BETIGI
# ═══════════════════════════════════════════════════════════
cat > /usr/local/bin/start-armpanel << 'STARTSCRIPT'
#!/bin/bash
# ArmPanel + bağımlı servisleri başlatır

nginx 2>/dev/null || true
php-fpm8.4 2>/dev/null || true

pkill -f "ttyd.*1570" 2>/dev/null || true
/etc/ttyd/ttyd.aarch64 -p 1570 -W tmux new -A -s armpanel &>/dev/null &

pkill -f "filebrowser" 2>/dev/null || true
filebrowser -d /etc/filebrowser/filebrowser.db -a 0.0.0.0 -p 8083 -r / &>/dev/null &

cd /root/armpanel
python3 app.py
STARTSCRIPT

chmod +x /usr/local/bin/start-armpanel

echo ""
echo "  +==========================================+"
echo "  |     Kurulum Tamamlandı!                  |"
echo "  |                                          |"
echo "  |   Panel:      http://localhost:1569      |"
echo "  |   ttyd:       http://localhost:1570      |"
echo "  |   Nginx:      http://localhost:8080      |"
echo "  |   AdGuard:    http://localhost:3000      |"
echo "  |   Nextcloud:  http://localhost:8080      |"
echo "  |   n8n:        http://localhost:5678      |"
echo "  |   Ghost:      http://localhost:2368      |"
echo "  |   MariaDB:    localhost:3306             |"
echo "  |   phpMyAdmin: http://localhost:8080/phpmyadmin |"
echo "  |   Jellyfin:   http://localhost:8096      |"
echo "  |   WireGuard:  udp/51820                  |"
echo "  |   Vaultwarden:http://localhost:8085      |"
echo "  |   UptimeKuma: http://localhost:3001      |"
echo "  |   Syncthing:  http://localhost:8384      |"
echo "  |   Samba:      smb://localhost:445        |"
echo "  |                                          |"
echo "  |   Kullanıcı: admin / admin               |"
echo "  |   Başlat: python3 /root/armpanel/app.py  |"
echo "  +==========================================+"
echo ""

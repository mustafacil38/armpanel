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
echo "[1/10] Mimari tespit ediliyor: $ARCH"

if [ "$ARCH" != "aarch64" ] && [ "$ARCH" != "arm64" ]; then
    echo "UYARI: Bu betik ARM64 için tasarlanmıştır. Mevcut: $ARCH"
fi

# ── 1. Temel sistem araçları ──
echo "[2/10] Temel sistem araçları kuruluyor..."
apt update -y
apt install -y curl wget git unzip zip tar \
    apt-transport-https ca-certificates gnupg procps \
    sudo cron logrotate net-tools iproute2 \
    htop tree ncdu jq nano less 2>/dev/null || true

# Eksik olabilecek paketleri ayrı ayrı dene
for pkg in software-properties-common lsb-release build-essential pkg-config; do
    apt install -y "$pkg" 2>/dev/null || echo "  -> $pkg bulunamadı, atlanıyor"
done

# ── 2. Python 3 + pip ──
echo "[3/10] Python 3 ve pip kuruluyor..."
apt install -y python3 python3-pip python3-venv python3-dev python3-full

# ── 3. Nginx ──
echo "[4/10] Nginx kuruluyor..."
apt install -y nginx

# Nginx'i proot ortamında başlatmak için systemd yerine doğrudan komut
# /etc/nginx/nginx.conf'da daemon off; veya arka plan modunda çalıştırılacak

# ── 4. PHP 8.4 FPM ──
echo "[5/10] PHP 8.4 FPM kuruluyor..."

# Debian 13 (Trixie) PHP 8.4'ü resmi depoda barındırır
# Eğer yoksa Sury deposu eklenir
if ! apt-cache show php8.4-fpm &>/dev/null; then
    echo "  -> PHP 8.4 resmi depoda bulunamadı, Sury deposu ekleniyor..."
    curl -sSLo /usr/share/keyrings/deb.sury.org-php.gpg https://packages.sury.org/php/apt.gpg
    echo "deb [signed-by=/usr/share/keyrings/deb.sury.org-php.gpg] https://packages.sury.org/php/ $(lsb_release -sc) main" > /etc/apt/sources.list.d/php.list
    apt update -y
fi

apt install -y php8.4-fpm php8.4-cli php8.4-common php8.4-mysql \
    php8.4-pgsql php8.4-sqlite3 php8.4-curl php8.4-xml php8.4-mbstring \
    php8.4-zip php8.4-gd php8.4-intl php8.4-opcache php8.4-readline

# ── 5. ttyd (Web Terminal) ──
echo "[6/10] ttyd kuruluyor..."

if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    TTYD_ARCH="aarch64"
elif [ "$ARCH" = "x86_64" ]; then
    TTYD_ARCH="x86_64"
else
    TTYD_ARCH="aarch64"  # Varsayılan
fi

TTYD_VERSION="1.7.7"
wget -q "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.${TTYD_ARCH}" -O /usr/local/bin/ttyd
chmod +x /usr/local/bin/ttyd
echo "  -> ttyd ${TTYD_VERSION} (${TTYD_ARCH}) kuruldu"

# ── 6. tmux ──
echo "[7/10] tmux kuruluyor..."
apt install -y tmux

# ── 7. File Browser ──
echo "[8/10] File Browser kuruluyor..."

if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    FB_ARCH="arm64"
elif [ "$ARCH" = "x86_64" ]; then
    FB_ARCH="amd64"
else
    FB_ARCH="arm64"
fi

FB_VERSION="2.32.0"
wget -q "https://github.com/filebrowser/filebrowser/releases/download/v${FB_VERSION}/linux-${FB_ARCH}-filebrowser.tar.gz" -O /tmp/filebrowser.tar.gz
tar xzf /tmp/filebrowser.tar.gz -C /tmp
mv /tmp/filebrowser /usr/local/bin/filebrowser
chmod +x /usr/local/bin/filebrowser
rm -f /tmp/filebrowser.tar.gz /tmp/LICENSE /tmp/README.md
echo "  -> File Browser ${FB_VERSION} kuruldu"

# ── 8. uDocker ──
echo "[9/10] uDocker kuruluyor..."

# uDocker Python ile kurulur (Termux/Debian proot uyumlu)
pip3 install udocker --break-system-packages

# uDocker ilk başlatma ayarları
udocker --help >/dev/null 2>&1 || true
echo "  -> uDocker kuruldu"

# ── 9. ArmPanel Projesi ──
echo "[10/10] ArmPanel projesi kuruluyor..."

INSTALL_DIR="/root/armpanel"

if [ -d "$INSTALL_DIR" ]; then
    echo "  -> Mevcut kurulum bulundu, güncelleniyor..."
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    git clone https://github.com/mustafacil38/armpanel.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Python bağımlılıkları
pip3 install -r requirements.txt --break-system-packages

# ── 10. Servis başlatma betikleri ──
echo ""
echo "  -> Servis başlatma betikleri oluşturuluyor..."

cat > /usr/local/bin/start-armpanel << 'STARTSCRIPT'
#!/bin/bash
# ArmPanel + bağımlı servisleri başlatır

# Nginx
nginx 2>/dev/null || true

# PHP-FPM
php-fpm8.4 2>/dev/null || true

# ttyd (Port 1570)
pkill -f "ttyd.*1570" 2>/dev/null || true
/etc/ttyd/ttyd.aarch64 -p 1570 -W tmux new -A -s armpanel &>/dev/null &

# File Browser (Port 8083)
pkill -f "filebrowser" 2>/dev/null || true
filebrowser -d /etc/filebrowser/filebrowser.db -a 0.0.0.0 -p 8083 -r / &>/dev/null &

# ArmPanel (Port 1569)
cd /root/armpanel
python3 app.py
STARTSCRIPT

chmod +x /usr/local/bin/start-armpanel

# ── 11. php-fpm proot ayarı ──
# Proot ortamında php-fpm pool dinleyici ayarı
if [ -f /etc/php/8.4/fpm/pool.d/www.conf ]; then
    # Eğer port yerine socket kullanıyorsa, nginx ile uyumlu hale getir
    sed -i 's|^listen = /run.*|listen = 127.0.0.1:9000|' /etc/php/8.4/fpm/pool.d/www.conf 2>/dev/null || true
fi

# ── 12. Nginx Ayarları ──
# Varsayılan nginx config'i PHP ile çalışır hale getir
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

echo ""
echo "  +==========================================+"
echo "  |     Kurulum Tamamlandı!                  |"
echo "  |                                          |"
echo "  |   Panel:  http://localhost:1569          |"
echo "  |   ttyd:   http://localhost:1570          |"
echo "  |   Nginx:  http://localhost:8080          |"
echo "  |   PHP:    127.0.0.1:9000                 |"
echo "  |   Files:  http://localhost:8083          |"
echo "  |                                          |"
echo "  |   Kullanıcı: admin                       |"
echo "  |   Şifre:     admin                       |"
echo "  |                                          |"
echo "  |   Başlatmak için:                        |"
echo "  |   python3 /root/armpanel/app.py          |"
echo "  +==========================================+"
echo ""

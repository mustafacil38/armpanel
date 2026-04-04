#!/bin/bash
# ============================================================
# ArmPanel - Kurulum Betiği
# Ortam: Termux > proot-distro (Debian 13/Trixie) > root
# NOT: Cihaz ROOTLU DEĞIL (bootloader kilitli). Proot ile çalışır.
# ============================================================

# ── Renkler ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

VERSION="1.0.0"
REPO_URL="https://github.com/mustafacil38/armpanel"
ARCH=$(uname -m)

if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    ARCH_LABEL="aarch64 (ARM64)"
else
    ARCH_LABEL="$ARCH"
fi

TOTAL_STEPS=21

# ═══════════════════════════════════════════════════════════
#  GÖRSEL BAŞLIK
# ═══════════════════════════════════════════════════════════
clear

echo ""
echo -e "${CYAN}${BOLD}    +==================================================+${NC}"
echo -e "${CYAN}${BOLD}    |                                                  |${NC}"
echo -e "${CYAN}${BOLD}    |   ${WHITE} ___  ___  ___  _  _  ___  ___  ___  ___ ${CYAN}   |${NC}"
echo -e "${CYAN}${BOLD}    |  ${WHITE} / _ \| _ )/ _ \| || || __|/ _ \| _ \/ __|${CYAN}  |${NC}"
echo -e "${CYAN}${BOLD}    | ${WHITE} | (_) | _ \ (_) | __ | _| | (_) |   /\__ \${CYAN}  |${NC}"
echo -e "${CYAN}${BOLD}    |  ${WHITE} \___/|___/\___/_||_||___|\___/|_|_\|___/${CYAN}   |${NC}"
echo -e "${CYAN}${BOLD}    |                                                  |${NC}"
echo -e "${CYAN}${BOLD}    |         ${WHITE}Mobil Sunucu Yonetim Paneli${CYAN}            |${NC}"
echo -e "${CYAN}${BOLD}    |                                                  |${NC}"
echo -e "${CYAN}${BOLD}    |  ${DIM}Surum: ${WHITE}${VERSION}${CYAN}                                      |${NC}"
echo -e "${CYAN}${BOLD}    |  ${DIM}${REPO_URL}${CYAN}  |${NC}"
echo -e "${CYAN}${BOLD}    |                                                  |${NC}"
echo -e "${CYAN}${BOLD}    +==================================================+${NC}"
echo ""
echo -e "${DIM}  Mimari: ${WHITE}${ARCH_LABEL}${NC}"
echo -e "${DIM}  Ortam:  ${WHITE}Debian 13 (Proot) - ROOTSUZ Cihaz${NC}"
echo ""

# ── Uygulama Listesi ──
echo -e "${BOLD}  Kurulacak Uygulamalar:${NC}"
echo -e "${DIM}  -------------------------------------------------------${NC}"

declare -a APP_NAMES=(
    "Temel Sistem Araclari"
    "Python 3 + pip"
    "Nginx"
    "PHP 8.4 FPM"
    "ttyd (Web Terminal)"
    "tmux"
    "File Browser"
    "Node.js + npm"
    "AdGuard Home"
    "Nextcloud"
    "n8n"
    "Ghost"
    "MariaDB"
    "phpMyAdmin"
    "Jellyfin"
    "WireGuard"
    "Vaultwarden (Bitwarden)"
    "Uptime Kuma"
    "rclone"
    "Syncthing"
    "Samba"
)

declare -a APP_STATUS=()
for i in "${!APP_NAMES[@]}"; do
    APP_STATUS[$i]="pending"
done

for i in "${!APP_NAMES[@]}"; do
    num=$((i + 1))
    printf "  ${DIM}%2d.${NC} %-38s ${YELLOW}Bekliyor...${NC}\n" "$num" "${APP_NAMES[$i]}"
done

echo -e "${DIM}  -------------------------------------------------------${NC}"
echo ""

# Cursor pozisyonu
LIST_START_LINE=$(($(tput lines) - ${#APP_NAMES[@]} - 4))

# ── Yardimci Fonksiyonlar ──
print_progress() {
    local current=$1
    local total=$2
    local pct=$((current * 100 / total))
    local filled=$((pct / 5))
    local empty=$((20 - filled))

    printf "\r${BOLD}  Genel Ilerleme: [${GREEN}"
    for ((i=0; i<filled; i++)); do printf "#"; done
    printf "${DIM}"
    for ((i=0; i<empty; i++)); do printf "-"; done
    printf "${NC}${BOLD}] %3d%%${NC}" "$pct"
}

update_status() {
    local idx=$1
    local status=$2
    APP_STATUS[$idx]="$status"
    local line_num=$((LIST_START_LINE + idx))
    local num=$((idx + 1))

    if [ "$status" = "loading" ]; then
        tput cup "$line_num" 0
        printf "  ${DIM}%2d.${NC} %-38s ${YELLOW}Yukleniyor...${NC}" "$num" "${APP_NAMES[$idx]}"
    elif [ "$status" = "done" ]; then
        tput cup "$line_num" 0
        printf "  ${DIM}%2d.${NC} %-38s ${GREEN}Tamamlandi${NC}" "$num" "${APP_NAMES[$idx]}"
    elif [ "$status" = "fail" ]; then
        tput cup "$line_num" 0
        printf "  ${DIM}%2d.${NC} %-38s ${RED}Basarisiz${NC}" "$num" "${APP_NAMES[$idx]}"
    fi

    local progress_line=$((LIST_START_LINE + ${#APP_NAMES[@]} + 1))
    tput cup "$progress_line" 0
    print_progress "$((idx + 1))" "$TOTAL_STEPS"
}

print_progress_line() {
    local progress_line=$((LIST_START_LINE + ${#APP_NAMES[@]} + 1))
    tput cup "$progress_line" 0
    print_progress "$1" "$TOTAL_STEPS"
}

echo ""
print_progress_line 0
echo ""

# ═══════════════════════════════════════════════════════════
#  KURULUM
# ═══════════════════════════════════════════════════════════

# 0. dpkg onarimi
update_status 0 "loading"
dpkg --configure -a 2>/dev/null || true
apt --fix-broken install -y >/dev/null 2>&1 || true
apt update -y >/dev/null 2>&1
apt install -y curl wget git unzip zip tar \
    apt-transport-https ca-certificates gnupg procps \
    sudo cron logrotate net-tools iproute2 \
    htop tree ncdu jq nano less >/dev/null 2>&1 || true
update_status 0 "done"

# 1. Python
update_status 1 "loading"
apt install -y python3 python3-pip python3-venv python3-dev python3-full >/dev/null 2>&1 || true
update_status 1 "done"

# 2. Nginx
update_status 2 "loading"
apt install -y nginx >/dev/null 2>&1 || true
update_status 2 "done"

# 3. PHP 8.4
update_status 3 "loading"
if ! apt-cache show php8.4-fpm &>/dev/null; then
    curl -sSLo /usr/share/keyrings/deb.sury.org-php.gpg https://packages.sury.org/php/apt.gpg 2>/dev/null
    echo "deb [signed-by=/usr/share/keyrings/deb.sury.org-php.gpg] https://packages.sury.org/php/ $(lsb_release -sc 2>/dev/null || echo 'trixie') main" > /etc/apt/sources.list.d/php.list
    apt update -y >/dev/null 2>&1
fi
apt install -y php8.4-fpm php8.4-cli php8.4-common php8.4-mysql \
    php8.4-pgsql php8.4-sqlite3 php8.4-curl php8.4-xml php8.4-mbstring \
    php8.4-zip php8.4-gd php8.4-intl php8.4-opcache php8.4-readline >/dev/null 2>&1 || true
if [ -f /etc/php/8.4/fpm/pool.d/www.conf ]; then
    sed -i 's|^listen = /run.*|listen = 127.0.0.1:9000|' /etc/php/8.4/fpm/pool.d/www.conf 2>/dev/null || true
fi
update_status 3 "done"

# 4. ttyd
update_status 4 "loading"
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then TTYD_ARCH="aarch64"; else TTYD_ARCH="x86_64"; fi
wget -q "https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.${TTYD_ARCH}" -O /usr/local/bin/ttyd 2>/dev/null
chmod +x /usr/local/bin/ttyd
update_status 4 "done"

# 5. tmux
update_status 5 "loading"
apt install -y tmux >/dev/null 2>&1 || true
update_status 5 "done"

# 6. File Browser
update_status 6 "loading"
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then FB_ARCH="arm64"; else FB_ARCH="amd64"; fi
wget -q "https://github.com/filebrowser/filebrowser/releases/download/v2.32.0/linux-${FB_ARCH}-filebrowser.tar.gz" -O /tmp/filebrowser.tar.gz 2>/dev/null
tar xzf /tmp/filebrowser.tar.gz -C /tmp 2>/dev/null
mv /tmp/filebrowser /usr/local/bin/filebrowser 2>/dev/null
chmod +x /usr/local/bin/filebrowser
rm -f /tmp/filebrowser.tar.gz
update_status 6 "done"

# 7. Node.js
update_status 7 "loading"
apt install -y nodejs npm >/dev/null 2>&1 || true
update_status 7 "done"

# 8. AdGuard Home
update_status 8 "loading"
mkdir -p /opt/adguardhome
AGH_VER=$(curl -s https://api.github.com/repos/AdguardTeam/AdGuardHome/releases/latest 2>/dev/null | grep tag_name | cut -d'"' -f4 | tr -d v)
wget -q "https://github.com/AdguardTeam/AdGuardHome/releases/download/v${AGH_VER}/AdGuardHome_linux_arm64.tar.gz" -O /tmp/adguardhome.tar.gz 2>/dev/null || true
if [ -f /tmp/adguardhome.tar.gz ]; then
    tar xzf /tmp/adguardhome.tar.gz -C /tmp 2>/dev/null
    mv /tmp/AdGuardHome/AdGuardHome /opt/adguardhome/AdGuardHome 2>/dev/null || true
    chmod +x /opt/adguardhome/AdGuardHome
    rm -rf /tmp/AdGuardHome /tmp/adguardhome.tar.gz
fi
update_status 8 "done"

# 9. Nextcloud
update_status 9 "loading"
mkdir -p /var/www/nextcloud
NC_VER=$(curl -s https://api.github.com/repos/nextcloud/server/releases/latest 2>/dev/null | grep tag_name | cut -d'"' -f4 | tr -d v)
wget -q "https://download.nextcloud.com/server/releases/latest.zip" -O /tmp/nextcloud.zip 2>/dev/null || true
if [ -f /tmp/nextcloud.zip ]; then
    unzip -q /tmp/nextcloud.zip -d /tmp 2>/dev/null
    cp -r /tmp/nextcloud/* /var/www/nextcloud/ 2>/dev/null || true
    chown -R www-data:www-data /var/www/nextcloud 2>/dev/null || true
    rm -rf /tmp/nextcloud /tmp/nextcloud.zip
fi
cat > /etc/nginx/sites-available/nextcloud << 'NCCONF'
server {
    listen 8080;
    server_name _;
    root /var/www/nextcloud;
    index index.php;
    client_max_body_size 512M;
    location / { try_files $uri $uri/ /index.php?$query_string; }
    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass 127.0.0.1:9000;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }
}
NCCONF
ln -sf /etc/nginx/sites-available/nextcloud /etc/nginx/sites-enabled/nextcloud 2>/dev/null || true
update_status 9 "done"

# 10. n8n
update_status 10 "loading"
npm install -g n8n >/dev/null 2>&1 || true
update_status 10 "done"

# 11. Ghost
update_status 11 "loading"
mkdir -p /var/www/ghost
npm install -g ghost-cli >/dev/null 2>&1 || true
cd /var/www/ghost && ghost install local --no-setup-linux-user --no-start >/dev/null 2>&1 || true
cd /root
update_status 11 "done"

# 12. MariaDB
update_status 12 "loading"
apt install -y mariadb-server mariadb-client >/dev/null 2>&1 || true
mkdir -p /run/mysqld && chown mysql:mysql /run/mysqld 2>/dev/null || true
update_status 12 "done"

# 13. phpMyAdmin
update_status 13 "loading"
PMA_VER=$(curl -s https://api.github.com/repos/phpmyadmin/phpmyadmin/releases/latest 2>/dev/null | grep tag_name | cut -d'"' -f4 | tr -d v)
wget -q "https://files.phpmyadmin.net/phpMyAdmin/${PMA_VER}/phpMyAdmin-${PMA_VER}-all-languages.zip" -O /tmp/pma.zip 2>/dev/null || true
if [ -f /tmp/pma.zip ]; then
    mkdir -p /var/www/html/phpmyadmin
    unzip -q /tmp/pma.zip -d /tmp 2>/dev/null
    cp -r /tmp/phpMyAdmin-${PMA_VER}-all-languages/* /var/www/html/phpmyadmin/ 2>/dev/null || true
    rm -rf /tmp/pma.zip /tmp/phpMyAdmin-*
fi
update_status 13 "done"

# 14. Jellyfin
update_status 14 "loading"
apt install -y jellyfin >/dev/null 2>&1 || true
mkdir -p /etc/jellyfin /var/cache/jellyfin
update_status 14 "done"

# 15. WireGuard
update_status 15 "loading"
apt install -y wireguard >/dev/null 2>&1 || true
update_status 15 "done"

# 16. Vaultwarden
update_status 16 "loading"
mkdir -p /opt/vaultwarden
VW_VER=$(curl -s https://api.github.com/repos/dani-garcia/vaultwarden/releases/latest 2>/dev/null | grep tag_name | cut -d'"' -f4 | tr -d v)
wget -q "https://github.com/dani-garcia/vaultwarden/releases/download/${VW_VER}/vaultwarden-${VW_VER}-aarch64-unknown-linux-musl.tar.gz" -O /tmp/vw.tar.gz 2>/dev/null || true
if [ -f /tmp/vw.tar.gz ]; then
    tar xzf /tmp/vw.tar.gz -C /tmp 2>/dev/null
    mv /tmp/vaultwarden /opt/vaultwarden/vaultwarden 2>/dev/null || true
    chmod +x /opt/vaultwarden/vaultwarden
    rm -f /tmp/vw.tar.gz
fi
update_status 16 "done"

# 17. Uptime Kuma
update_status 17 "loading"
mkdir -p /opt/uptime-kuma
UK_VER=$(curl -s https://api.github.com/repos/louislam/uptime-kuma/releases/latest 2>/dev/null | grep tag_name | cut -d'"' -f4 | tr -d v)
wget -q "https://github.com/louislam/uptime-kuma/releases/download/${UK_VER}/uptime-kuma-${UK_VER}.tar.gz" -O /tmp/uk.tar.gz 2>/dev/null || true
if [ -f /tmp/uk.tar.gz ]; then
    tar xzf /tmp/uk.tar.gz -C /opt/uptime-kuma 2>/dev/null
    cd /opt/uptime-kuma && npm install --production >/dev/null 2>&1 || true
    rm -f /tmp/uk.tar.gz
fi
update_status 17 "done"

# 18. rclone
update_status 18 "loading"
curl -sSf https://rclone.org/install.sh | bash >/dev/null 2>&1 || true
update_status 18 "done"

# 19. Syncthing
update_status 19 "loading"
apt install -y syncthing >/dev/null 2>&1 || true
update_status 19 "done"

# 20. Samba
update_status 20 "loading"
apt install -y samba >/dev/null 2>&1 || true
update_status 20 "done"

# ═══════════════════════════════════════════════════════════
#  NGINX CONFIG
# ═══════════════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════════════
#  ARMPANEL
# ═══════════════════════════════════════════════════════════
INSTALL_DIR="/root/armpanel"
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR"
    git pull origin main >/dev/null 2>&1 || true
else
    git clone https://github.com/mustafacil38/armpanel.git "$INSTALL_DIR" >/dev/null 2>&1
    cd "$INSTALL_DIR"
fi
pip3 install -r requirements.txt --break-system-packages >/dev/null 2>&1

cat > /usr/local/bin/start-armpanel << 'STARTSCRIPT'
#!/bin/bash
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

# ═══════════════════════════════════════════════════════════
#  FİNAL
# ═══════════════════════════════════════════════════════════
FINAL_LINE=$((LIST_START_LINE + ${#APP_NAMES[@]} + 3))
tput cup "$FINAL_LINE" 0

echo ""
echo ""
echo -e "${GREEN}${BOLD}  +==================================================+${NC}"
echo -e "${GREEN}${BOLD}  |                                                  |${NC}"
echo -e "${GREEN}${BOLD}  |           ${WHITE}Kurulus Basariyla Tamamlandi!${GREEN}            |${NC}"
echo -e "${GREEN}${BOLD}  |                                                  |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}Panel:      ${WHITE}http://localhost:1569${GREEN}               |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}ttyd:       ${WHITE}http://localhost:1570${GREEN}               |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}Nginx:      ${WHITE}http://localhost:8080${GREEN}               |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}AdGuard:    ${WHITE}http://localhost:3000${GREEN}               |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}Nextcloud:  ${WHITE}http://localhost:8080/nextcloud${GREEN}     |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}n8n:        ${WHITE}http://localhost:5678${GREEN}               |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}Ghost:      ${WHITE}http://localhost:2368${GREEN}               |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}MariaDB:    ${WHITE}localhost:3306${GREEN}                      |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}phpMyAdmin: ${WHITE}http://localhost:8080/phpmyadmin${GREEN}    |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}Jellyfin:   ${WHITE}http://localhost:8096${GREEN}               |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}WireGuard:  ${WHITE}udp/51820${GREEN}                           |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}Vaultwarden:${WHITE}http://localhost:8085${GREEN}               |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}UptimeKuma: ${WHITE}http://localhost:3001${GREEN}               |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}Syncthing:  ${WHITE}http://localhost:8384${GREEN}               |${NC}"
echo -e "${GREEN}${BOLD}  |  ${CYAN}Samba:      ${WHITE}smb://localhost:445${GREEN}                 |${NC}"
echo -e "${GREEN}${BOLD}  |                                                  |${NC}"
echo -e "${GREEN}${BOLD}  |  ${DIM}Kullanici: ${WHITE}admin${NC}  ${DIM}Sifre: ${WHITE}admin${NC}${GREEN}                   |${NC}"
echo -e "${GREEN}${BOLD}  |  ${DIM}Baslat: ${WHITE}python3 /root/armpanel/app.py${NC}${GREEN}          |${NC}"
echo -e "${GREEN}${BOLD}  |                                                  |${NC}"
echo -e "${GREEN}${BOLD}  +==================================================+${NC}"
echo ""
echo ""

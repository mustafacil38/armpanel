#!/bin/bash
# ============================================================
# ArmPanel - Güncelleme Betiği
# Mevcut dosyaları temizler, depodan en güncel sürümü çeker
# ============================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${BLUE}  +==========================================+${NC}"
echo -e "${BLUE}  |     ArmPanel Güncelleme                  |${NC}"
echo -e "${BLUE}  +==========================================+${NC}"
echo ""

# ── 1. Mevcut dosyaları temizle ──
echo -e "${YELLOW}[1/4] Mevcut dosyalar temizleniyor...${NC}"

# Korunacak klasörler/dosyalar (veri kaybı olmaması için)
PROTECTED="armpanel.db armpanel.db-wal armpanel.db-shm .git .gitignore"

# Korunacak dosyaları listele
PROTECTED_FILES=""
for item in $PROTECTED; do
    if [ -e "$INSTALL_DIR/$item" ]; then
        PROTECTED_FILES="$PROTECTED_FILES $item"
    fi
done

# Geçici klasöre taşı
TMP_BACKUP=$(mktemp -d)
for item in $PROTECTED_FILES; do
    cp -r "$INSTALL_DIR/$item" "$TMP_BACKUP/" 2>/dev/null || true
done

# Tüm dosyaları sil (.git ve korunacaklar hariç)
find "$INSTALL_DIR" -maxdepth 1 \
    ! -name '.' \
    ! -name '.git' \
    ! -name 'update.sh' \
    ! -name 'install.sh' \
    -exec rm -rf {} +

echo -e "${GREEN}  -> Temizleme tamamlandı${NC}"

# ── 2. Depodan çek ──
echo -e "${YELLOW}[2/4] GitHub'dan en güncel sürüm indiriliyor...${NC}"

cd "$INSTALL_DIR"

# Eğer git repo yoksa clone yap
if [ ! -d ".git" ]; then
    echo -e "${BLUE}  -> Git repo bulunamadı, klonlanıyor...${NC}"
    cd /root
    rm -rf armpanel
    git clone https://github.com/mustafacil38/armpanel.git
    cd /root/armpanel
    INSTALL_DIR="/root/armpanel"
else
    # Mevcut repoyu sıfırla ve güncelle
    git fetch origin main
    git reset --hard origin/main
    git clean -fd
fi

echo -e "${GREEN}  -> Güncel dosyalar indirildi${NC}"

# ── 3. Korunan dosyaları geri yükle ──
echo -e "${YELLOW}[3/4] Veri dosyaları geri yükleniyor...${NC}"

if [ -d "$TMP_BACKUP" ]; then
    for item in $(ls "$TMP_BACKUP"); do
        cp -r "$TMP_BACKUP/$item" "$INSTALL_DIR/" 2>/dev/null || true
    done
    rm -rf "$TMP_BACKUP"
    echo -e "${GREEN}  -> Veri dosyaları korundu${NC}"
else
    echo -e "${BLUE}  -> Korunacak veri dosyası bulunamadı${NC}"
fi

# ── 4. Python bağımlılıklarını güncelle ──
echo -e "${YELLOW}[4/4] Python bağımlılıkları güncelleniyor...${NC}"

cd "$INSTALL_DIR"

if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --break-system-packages --quiet
    echo -e "${GREEN}  -> Bağımlılıklar güncellendi${NC}"
else
    echo -e "${RED}  -> requirements.txt bulunamadı!${NC}"
fi

echo ""
echo -e "${GREEN}  +==========================================+"
echo -e "${GREEN}  |     Güncelleme Tamamlandı!               |"
echo -e "${GREEN}  |                                          |"
echo -e "${GREEN}  |   Panel:  http://localhost:1569          |"
echo -e "${GREEN}  |   ttyd:   http://localhost:1570          |"
echo -e "${GREEN}  |   Nginx:  http://localhost:8080          |"
echo -e "${GREEN}  |   Files:  http://localhost:8083          |"
echo -e "${GREEN}  |                                          |"
echo -e "${GREEN}  |   Başlatmak için:                        |"
echo -e "${GREEN}  |   python3 $INSTALL_DIR/app.py            |"
echo -e "${GREEN}  +==========================================+"
echo ""

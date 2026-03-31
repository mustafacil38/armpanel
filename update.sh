#!/bin/bash

# ArmPanel Git Güncelleyici (Push)
# Bu betik yerel değişiklikleri GitHub'a göndermek için kullanılır.

# Renk tanımlamaları
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}>>> ArmPanel Git Güncelleyici Başlatıldı...${NC}"

# Tüm değişiklikleri ekle
echo -e "${BLUE}>>> Değişiklikler taranıyor ve ekleniyor...${NC}"
git add .

# Değişen dosyaları göster
git status -s

# Commit mesajı ayarla (Parametre verilirse o kullanılır, yoksa tarih atılır)
if [ -n "$1" ]; then
    MSG="$1"
else
    MSG="Güncelleme: $(date '+%Y-%m-%d %H:%M:%S')"
fi

# Yerel commit oluştur
echo -e "${BLUE}>>> Değişiklikler paketleniyor: ${MSG}${NC}"
git commit -m "$MSG"

# GitHub'a gönder
echo -e "${BLUE}>>> GitHub'a (origin main) gönderiliyor...${NC}"
git push origin main

# Sonuç kontrolü
if [ $? -eq 0 ]; then
    echo -e "${GREEN}>>> [BAŞARILI] Proje GitHub'a yüklendi.${NC}"
else
    echo -e "${RED}>>> [HATA] GitHub'a gönderilemedi. Lütfen internet bağlantınızı veya git yetkilerinizi kontrol edin.${NC}"
fi

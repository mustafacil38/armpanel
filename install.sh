#!/bin/bash

# 1. Adım: Sistemi Güncelle
echo "--- Paket listesi güncelleniyor... ---"
apt update

# 2. Adım: Paketleri Kur (-y parametresi otomatik onay verir)
echo "--- Gerekli araçlar kuruluyor... ---"
# apt install -y git curl wget python3 ttyd

# 3. Adım: Kurulum Kontrolü
echo "--- Kurulum tamamlandı. Versiyonlar kontrol ediliyor: ---"
ttyd --version
python3 --version

echo "--- Her şey hazır! ---"
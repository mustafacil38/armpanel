#!/bin/bash

# 1. Adım: Sistemi Güncelle
echo "--- Paket listesi güncelleniyor... ---"
apt update -y
# 2. Adım: Gerekli Paketleri Kur (-y parametresi otomatik onay verir)
echo "--- Gerekli Paketler Kuruluyor... ---"
apt install -y git wget python3.13 ttyd nginx
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:ondrej/php
sudo apt install -y php8.4
curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash
cd\
git clone https://github.com/mustafacil38/armpanel.git
cd/root/armpanel
pip install -r requirements.txt --break-system-packages

# 3. Adım: Kurulum Kontrolü
echo "--- Kurulum tamamlandı. Versiyonlar kontrol ediliyor: ---"
ttyd --version
python3 --version
nginx --version
filebrowser --version
php --version

echo "--- Her şey hazır! ---"
python3.13 app.py

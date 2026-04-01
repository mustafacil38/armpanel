#!/bin/bash

# Adım: Sistemi Güncelle
echo "--- Paket listesi güncelleniyor... ---"
apt update -y
# Gerekli Paketleri Kur (-y parametresi otomatik onay verir)

# Sistem paketlerini yükle
apt update && apt install -y git wget python3.13 python3-pip ttyd nginx software-properties-common

# PHP 8.4 deposunu ekle ve yükle
add-apt-repository ppa:ondrej/php -y
apt update
apt install -y php8.4

# File Browser kurulumu
curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash

# Proje dizinine geçiş ve kurulum
cd /root
git clone https://github.com/mustafacil38/armpanel.git
cd /root/armpanel

# Python gereksinimlerini yükle
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

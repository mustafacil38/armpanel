# 1. Önce temel araçları ve depo yönetim araçlarını yükle
apt update
apt install -y curl wget git software-properties-common apt-transport-https lsb-release ca-certificates

# 2. PHP 8.4 için Sury deposunu Debian'a ekle (Ubuntu PPA burada çalışmaz)
curl -sSLo /usr/share/keyrings/deb.sury.org-php.gpg https://packages.sury.org/php/apt.gpg
echo "deb [signed-by=/usr/share/keyrings/deb.sury.org-php.gpg] https://packages.sury.org/php/ $(lsb_release -sc) main" > /etc/apt/sources.list.d/php.list

# 3. Python 3.13 Debian depolarında yoktur, Python 3 ve pip'i kur (Sistem sürümü kullanılır)
apt update
apt install -y python3 python3-pip python3-venv

# 4. ttyd ve php8.4 kurulumu
apt install -y php8.4 nginx
# ttyd Debian depolarında yoksa binary olarak çekelim
wget https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 -O /usr/local/bin/ttyd
chmod +x /usr/local/bin/ttyd

# 5. File Browser kurulumu
curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash

# 6. Proje Kurulumu
cd /root
git clone https://github.com/mustafacil38/armpanel.git
cd /root/armpanel

# 7. Gereksinimleri yükle (Debian'da --break-system-packages kullanımı gereklidir)
pip install -r requirements.txt --break-system-packages

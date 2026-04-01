# ArmPanel - Mobil Konsol

Mustafa'nın Mobil Konsolu, arm64 mimarili işlemcisi olan ve root erişimi olmayan Android cihazlarda Termux/Debian üzerinde çalışmak üzere geliştirilmiş modern bir web yönetim panelidir.

## 🚀 Hızlı Başlangıç

Bu projeyi başka bir cihazda kurmak için aşağıdaki adımları izleyin:

### 1. Gereksinimler
Sisteminizde Python 3'ün kurulu olduğundan emin olun.

**Debian/Ubuntu/Termux:**
```bash
apt update
apt install python3 python3-pip git
```

### 2. Projeyi İndirin
(Henüz indirmediyseniz)
```bash
git clone https://github.com/mustafacil38/armpanel.git
cd armpanel
```

### 3. Bağımlılıkları Kurun
```bash
pip install -r requirements.txt
pip install -r requirements.txt --break-system-packages
```

### 4. Paneli Başlatın
```bash
python3 app.py
python3.13 app.py
```

Panel varsayılan olarak **1569** portunda çalışacaktır.
Tarayıcınızdan şu adrese gidin: `http://localhost:1569`

**Varsayılan Giriş Bilgileri:**
- **Kullanıcı:** `admin`
- **Şifre:** `admin`

---

## 🛠 Servis Gereksinimleri

Panelin tüm özelliklerini (Servis Yönetimi ve Yükleyici) kullanabilmek için aşağıdaki paketlerin sisteminizde kurulu olması önerilir:

- **Nginx:** Web sunucusu için.
- **PHP 8.2-FPM:** PHP desteği için.
- **ttyd:** Terminal erişimi ve uygulama yükleyici için (Port: **1570**).
- **File Browser:** Dosya yönetimi için.
- **Cloudflared:** Uzak erişim (Tunnel) için.

Bu servislerin kurulu olması durumunda ArmPanel otomatik olarak onları yönetmeye başlayacaktır.

---

## 📂 Dosya Yapısı

- `app.py`: Ana sunucu dosyası.
- `config.py`: Port ve servis ayarları.
- `apps.txt`: Uygulama yükleyici listesi.
- `static/`: Stil ve JavaScript motorları.
- `templates/`: HTML arayüz şablonları.
- `routes/`: API uç noktaları (Backend mantığı).

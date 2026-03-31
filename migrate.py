import sqlite3
import os

db_path = 'armpanel.db'

def migrate():
    if not os.path.exists(db_path):
        print(f"Hata: {db_path} bulunamadı.")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. services tablosuna is_autostart ekle
    try:
        c.execute("ALTER TABLE services ADD COLUMN is_autostart INTEGER DEFAULT 0")
        print("Sütun 'is_autostart' başarıyla eklendi.")
    except sqlite3.OperationalError:
        print("Bilgi: 'is_autostart' sütunu zaten mevcut.")

    # 2. settings tablosuna cf_autostart ekle
    try:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('cf_autostart', '0')")
        print("Cloudflare auto-start ayarı eklendi.")
    except Exception as e:
        print(f"Hata (Settings): {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()

# REDBOX OS

REDBOX OS, gıda üretim işletmeleri için geliştirilmiş masaüstü üretim ve operasyon yönetim sistemidir.

## Ana Modüller

- Ana Sayfa ve yönetim göstergeleri
- Hammadde kabul ve stok yönetimi
- Reçete ve üretim yönetimi
- Paketleme kayıtları
- Sevkiyat yönetimi
- İzlenebilirlik
- Temizlik ve hijyen planları
- Kalite ve CAPA yönetimi
- Personel ve kullanıcı yetkilendirme
- PDF ve Excel raporları
- Sistem ve denetim kayıtları

## Sistem Gereksinimleri

- Python 3.14.6
- SQLite
- Tkinter
- requirements.txt dosyasında belirtilen Python paketleri

## Geliştirme Ortamı Kurulumu

    python3.14 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    python app.py

## Veri Güvenliği

Canlı veritabanı dosyası:

    database/redbox_os.db

Bu dosya işletmenin gerçek kayıtlarını içerir. Güncelleme, taşıma ve kurulum işlemlerinden önce mutlaka yedeklenmelidir.

## Sürüm

REDBOX OS v1.0.0

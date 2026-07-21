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

Geliştirme ortamındaki canlı veritabanı:

    database/redbox_os.db

Paketlenmiş macOS uygulamasındaki kullanıcı verileri:

    ~/Library/Application Support/REDBOX_OS/

İşletme verileri uygulama paketinin dışında tutulur. Güncelleme, taşıma ve kurulum işlemlerinden önce doğrulanmış yedek alınmalıdır.

## Dağıtım Belgeleri

- `docs/KULLANICI_KILAVUZU.md`
- `docs/KURULUM_KILAVUZU_MACOS.md`
- `docs/LISANS_VE_DESTEK.md`
- `docs/SURUM_NOTLARI_1.1.0.md`
- `docs/USB_DEMO_TESLIM_KILAVUZU.md`

## Sürüm

REDBOX OS v1.1.0 (Build 2)

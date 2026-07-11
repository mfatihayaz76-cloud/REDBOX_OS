import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "redbox_os.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS sistem_ayarlari (
        anahtar TEXT PRIMARY KEY,
        deger TEXT NOT NULL,
        aciklama TEXT
    );

    CREATE TABLE IF NOT EXISTS hammaddeler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT NOT NULL UNIQUE,
        birim TEXT NOT NULL DEFAULT 'kg',
        aktif INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS depo_kabul (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kabul_tarihi TEXT NOT NULL,
        hammadde_id INTEGER NOT NULL,
        tedarikci TEXT,
        tedarikci_lot_no TEXT NOT NULL,
        uretim_tarihi TEXT,
        skt_tett TEXT,
        miktar_kg REAL NOT NULL CHECK(miktar_kg >= 0),
        kabul_durumu TEXT NOT NULL DEFAULT 'KABUL',
        aciklama TEXT,
        kayit_zamani TEXT NOT NULL,
        FOREIGN KEY (hammadde_id) REFERENCES hammaddeler(id)
    );

    CREATE TABLE IF NOT EXISTS uretim (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uretim_tarihi TEXT NOT NULL,
        urun_lot_no TEXT NOT NULL UNIQUE,
        parti_sayisi INTEGER NOT NULL CHECK(parti_sayisi > 0),
        teorik_uretim_kg REAL NOT NULL,
        uretim_firesi_kg REAL NOT NULL DEFAULT 0,
        net_uretim_kg REAL NOT NULL,
        personel_1 TEXT NOT NULL DEFAULT 'Fatih Ayaz',
        personel_2 TEXT NOT NULL DEFAULT 'Eda Ayaz',
        aciklama TEXT,
        kayit_zamani TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS uretim_hammadde_lotlari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uretim_id INTEGER NOT NULL,
        depo_kabul_id INTEGER NOT NULL,
        kullanilan_miktar_kg REAL NOT NULL CHECK(kullanilan_miktar_kg >= 0),
        FOREIGN KEY (uretim_id) REFERENCES uretim(id) ON DELETE CASCADE,
        FOREIGN KEY (depo_kabul_id) REFERENCES depo_kabul(id),
        UNIQUE (uretim_id, depo_kabul_id)
    );

    CREATE TABLE IF NOT EXISTS paketleme (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paketleme_tarihi TEXT NOT NULL,
        uretim_id INTEGER NOT NULL,
        ambalaj_gram INTEGER NOT NULL CHECK(ambalaj_gram IN (500, 2500)),
        paket_adedi INTEGER NOT NULL CHECK(paket_adedi >= 0),
        paketlenen_kg REAL NOT NULL,
        paketleme_firesi_kg REAL NOT NULL DEFAULT 0,
        aciklama TEXT,
        kayit_zamani TEXT NOT NULL,
        FOREIGN KEY (uretim_id) REFERENCES uretim(id)
    );


    CREATE TABLE IF NOT EXISTS musteriler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        musteri_adi TEXT NOT NULL UNIQUE,
        aktif INTEGER NOT NULL DEFAULT 1,
        kayit_zamani TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sevkiyat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sevkiyat_tarihi TEXT NOT NULL,
        sevk_koli_adedi INTEGER NOT NULL DEFAULT 0,
        sevk_acik_paket_adedi INTEGER NOT NULL DEFAULT 0,
        musteri TEXT NOT NULL,
        musteri_id INTEGER,
        arac_plaka TEXT,
        belge_no TEXT,
        soguk_zincir INTEGER NOT NULL DEFAULT 1,
        aciklama TEXT,
        kayit_zamani TEXT NOT NULL,
        FOREIGN KEY (musteri_id)
            REFERENCES musteriler(id)
    );

    CREATE TABLE IF NOT EXISTS sevkiyat_kalemleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sevkiyat_id INTEGER NOT NULL,
        paketleme_id INTEGER NOT NULL,
        paket_adedi INTEGER NOT NULL,
        sevk_kg REAL NOT NULL,
        FOREIGN KEY (sevkiyat_id)
            REFERENCES sevkiyat(id),
        FOREIGN KEY (paketleme_id)
            REFERENCES paketleme(id)
    );


    CREATE TABLE IF NOT EXISTS temizlik (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT NOT NULL,
        alan_ekipman TEXT NOT NULL,
        yapilan_islem TEXT NOT NULL,
        uygulayan TEXT NOT NULL,
        kontrol_eden TEXT,
        durum TEXT NOT NULL DEFAULT 'UYGUN',
        aciklama TEXT,
        kayit_zamani TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_depo_lot
    ON depo_kabul(tedarikci_lot_no);

    CREATE INDEX IF NOT EXISTS idx_uretim_lot
    ON uretim(urun_lot_no);

    CREATE INDEX IF NOT EXISTS idx_paketleme_uretim
    ON paketleme(uretim_id);


    CREATE INDEX IF NOT EXISTS idx_sevkiyat_kalemleri_sevkiyat
    ON sevkiyat_kalemleri(sevkiyat_id);

    CREATE INDEX IF NOT EXISTS idx_sevkiyat_kalemleri_paketleme
    ON sevkiyat_kalemleri(paketleme_id);

    """)

    ayarlar = [
        ("PARTI_TEORIK_KG", "20.412", "Bir üretim partisinin teorik kg miktarı"),
        ("AKTIF_AMBALAJ_1_G", "500", "Aktif 500 g ambalaj"),
        ("AKTIF_AMBALAJ_2_G", "2500", "Aktif 2.5 kg ambalaj"),
        ("URUN_RAF_OMRU_AY", "12", "Long Potato raf ömrü"),
        ("DONUK_DEPOLAMA_C", "-18", "Donuk depolama sıcaklığı")
    ]

    cur.executemany("""
        INSERT OR IGNORE INTO sistem_ayarlari
        (anahtar, deger, aciklama)
        VALUES (?, ?, ?)
    """, ayarlar)

    hammaddeler = [
        ("Patates Unu", "kg"),
        ("Nişasta", "kg"),
        ("Mısır Unu", "kg"),
        ("Koruyucu", "kg"),
        ("Tavuk Çeşnisi", "kg"),
        ("Sarımsak Tozu", "kg"),
        ("Karabiber", "kg"),
        ("Tuz", "kg"),
        ("Metilselüloz Benecel A4M E461", "kg")
    ]

    cur.executemany("""
        INSERT OR IGNORE INTO hammaddeler (ad, birim)
        VALUES (?, ?)
    """, hammaddeler)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS tedarikciler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tedarikci_adi TEXT NOT NULL UNIQUE COLLATE NOCASE,
            aktif INTEGER NOT NULL DEFAULT 1,
            kayit_zamani TEXT NOT NULL
        )
    """)

    depo_kabul_kolonlari = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(depo_kabul)"
        ).fetchall()
    }

    if "tedarikci_id" not in depo_kabul_kolonlari:
        conn.execute("""
            ALTER TABLE depo_kabul
            ADD COLUMN tedarikci_id INTEGER
            REFERENCES tedarikciler(id)
        """)

    conn.commit()
    conn.close()

    print("REDBOX OS VERITABANI HAZIR")
    print(f"Veritabani: {DB_PATH}")
    print(f"Olusturma/Kontrol: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")


if __name__ == "__main__":
    init_database()

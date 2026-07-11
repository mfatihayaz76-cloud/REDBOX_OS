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


    CREATE TABLE IF NOT EXISTS mamul_stok_hareketleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hareket_tarihi TEXT NOT NULL,
        paketleme_id INTEGER NOT NULL,
        hareket_tipi TEXT NOT NULL CHECK(
            hareket_tipi IN (
                'TARIHSEL_KAPANIS',
                'IADE',
                'IMHA',
                'SAYIM_DUZELTME'
            )
        ),
        yon TEXT NOT NULL CHECK(
            yon IN ('GIRIS', 'CIKIS')
        ),
        paket_adedi INTEGER NOT NULL CHECK(
            paket_adedi > 0
        ),
        aciklama TEXT,
        kayit_zamani TEXT NOT NULL,
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


    conn.executescript("""
        CREATE TABLE IF NOT EXISTS receteler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT NOT NULL UNIQUE,
            parti_teorik_kg REAL NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS recete_kalemleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recete_id INTEGER NOT NULL,
            hammadde_id INTEGER NOT NULL,
            miktar_kg REAL NOT NULL,
            FOREIGN KEY (recete_id)
                REFERENCES receteler(id),
            FOREIGN KEY (hammadde_id)
                REFERENCES hammaddeler(id),
            UNIQUE(recete_id, hammadde_id)
        );

        CREATE TABLE IF NOT EXISTS uretim_recete (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uretim_id INTEGER NOT NULL UNIQUE,
            recete_id INTEGER NOT NULL,
            FOREIGN KEY (uretim_id)
                REFERENCES uretim(id),
            FOREIGN KEY (recete_id)
                REFERENCES receteler(id)
        );

        CREATE TABLE IF NOT EXISTS
        uretim_hammadde_lot_parti_araliklari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uretim_id INTEGER NOT NULL,
            hammadde_id INTEGER NOT NULL,
            depo_kabul_id INTEGER NOT NULL,
            parti_baslangic INTEGER NOT NULL,
            parti_bitis INTEGER NOT NULL,
            kullanilan_miktar_kg REAL NOT NULL,
            kayit_tipi TEXT NOT NULL
                DEFAULT 'KESIN_PARTI_ARALIGI',
            kayit_zamani TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uretim_id)
                REFERENCES uretim(id)
                ON DELETE CASCADE,
            FOREIGN KEY (hammadde_id)
                REFERENCES hammaddeler(id),
            FOREIGN KEY (depo_kabul_id)
                REFERENCES depo_kabul(id),
            CHECK (parti_baslangic > 0),
            CHECK (
                parti_bitis >= parti_baslangic
            ),
            CHECK (
                kullanilan_miktar_kg >= 0
            )
        );

        CREATE INDEX IF NOT EXISTS
        idx_uhlpa_depo_kabul
        ON
        uretim_hammadde_lot_parti_araliklari
        (
            depo_kabul_id
        );

        CREATE INDEX IF NOT EXISTS
        idx_uhlpa_uretim_hammadde
        ON
        uretim_hammadde_lot_parti_araliklari
        (
            uretim_id,
            hammadde_id,
            parti_baslangic
        );

        CREATE TABLE IF NOT EXISTS personeller (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL COLLATE NOCASE,
            gorev TEXT,
            aktif INTEGER NOT NULL DEFAULT 1,
            aciklama TEXT,
            kayit_zamani TEXT NOT NULL,
            UNIQUE(ad_soyad)
        );

        CREATE TABLE IF NOT EXISTS personel_yetkileri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personel_id INTEGER NOT NULL,
            yetki_kodu TEXT NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1,
            kayit_zamani TEXT NOT NULL,
            FOREIGN KEY (personel_id)
                REFERENCES personeller(id),
            UNIQUE(personel_id, yetki_kodu)
        );
    """)

    # REDBOX OS fresh-install business seed.
    # These values mirror the validated live operational contract.
    conn.execute("""
        INSERT OR IGNORE INTO receteler
        (
            ad,
            parti_teorik_kg,
            aktif
        )
        VALUES (?, ?, ?)
    """, (
        "LONG POTATO ANA RECETE",
        20.412,
        1,
    ))

    recete_id = conn.execute("""
        SELECT id
        FROM receteler
        WHERE ad = ?
    """, (
        "LONG POTATO ANA RECETE",
    )).fetchone()[0]

    recete_kalemleri = [
        ("Patates Unu", 5.200),
        ("Nişasta", 2.560),
        ("Mısır Unu", 1.280),
        (
            "Metilselüloz Benecel A4M E461",
            0.120,
        ),
        ("Tavuk Çeşnisi", 0.320),
        ("Sarımsak Tozu", 0.064),
        ("Karabiber", 0.024),
        ("Tuz", 0.144),
    ]

    for hammadde_adi, miktar_kg in recete_kalemleri:
        hammadde_row = conn.execute("""
            SELECT id
            FROM hammaddeler
            WHERE ad = ?
        """, (
            hammadde_adi,
        )).fetchone()

        if hammadde_row is None:
            raise RuntimeError(
                "Fresh bootstrap hammadde eksik: "
                + hammadde_adi
            )

        conn.execute("""
            INSERT OR IGNORE INTO recete_kalemleri
            (
                recete_id,
                hammadde_id,
                miktar_kg
            )
            VALUES (?, ?, ?)
        """, (
            recete_id,
            hammadde_row[0],
            miktar_kg,
        ))

    personel_seed = [
        (
            "Eda Ayaz",
            "Üretim / Operasyon",
        ),
        (
            "Fatih Ayaz",
            "Üretim / Operasyon",
        ),
    ]

    kayit_zamani = datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )

    for ad_soyad, gorev in personel_seed:
        conn.execute("""
            INSERT OR IGNORE INTO personeller
            (
                ad_soyad,
                gorev,
                aktif,
                kayit_zamani
            )
            VALUES (?, ?, 1, ?)
        """, (
            ad_soyad,
            gorev,
            kayit_zamani,
        ))

    personel_yetki_seed = [
        (
            "Eda Ayaz",
            "PAKETLEME",
        ),
        (
            "Eda Ayaz",
            "TEMIZLIK",
        ),
        (
            "Eda Ayaz",
            "URETIM",
        ),
        (
            "Fatih Ayaz",
            "DEPO_KABUL",
        ),
        (
            "Fatih Ayaz",
            "PAKETLEME",
        ),
        (
            "Fatih Ayaz",
            "SEVKIYAT",
        ),
        (
            "Fatih Ayaz",
            "TEMIZLIK",
        ),
        (
            "Fatih Ayaz",
            "URETIM",
        ),
    ]

    for ad_soyad, yetki_kodu in personel_yetki_seed:
        personel_id = conn.execute("""
            SELECT id
            FROM personeller
            WHERE ad_soyad = ?
        """, (
            ad_soyad,
        )).fetchone()[0]

        conn.execute("""
            INSERT OR IGNORE INTO personel_yetkileri
            (
                personel_id,
                yetki_kodu,
                aktif,
                kayit_zamani
            )
            VALUES (?, ?, 1, ?)
        """, (
            personel_id,
            yetki_kodu,
            kayit_zamani,
        ))

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

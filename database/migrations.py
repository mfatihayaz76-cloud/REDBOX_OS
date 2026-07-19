import sqlite3
from datetime import datetime
from pathlib import Path


LATEST_SCHEMA_VERSION = 10


QUALITY_CAPA_SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS kalite_uygunsuzluklari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kayit_no TEXT NOT NULL UNIQUE,
        kayit_tarihi TEXT NOT NULL,
        tespit_tarihi TEXT NOT NULL,
        kaynak_turu TEXT NOT NULL CHECK(
            kaynak_turu IN (
                'DEPO_KABUL',
                'URETIM',
                'PAKETLEME',
                'SEVKIYAT',
                'TEMIZLIK',
                'MUSTERI_SIKAYETI',
                'TEDARIKCI',
                'DIGER'
            )
        ),
        kategori TEXT NOT NULL,
        baslik TEXT NOT NULL,
        aciklama TEXT NOT NULL,
        onem_derecesi TEXT NOT NULL CHECK(
            onem_derecesi IN (
                'DUSUK',
                'ORTA',
                'YUKSEK',
                'KRITIK'
            )
        ),
        durum TEXT NOT NULL DEFAULT 'ACIK' CHECK(
            durum IN (
                'ACIK',
                'INCELEMEDE',
                'AKSIYONDA',
                'DOGRULAMADA',
                'KAPALI',
                'IPTAL'
            )
        ),
        depo_kabul_id INTEGER,
        uretim_id INTEGER,
        paketleme_id INTEGER,
        sevkiyat_id INTEGER,
        tedarikci_id INTEGER,
        musteri_id INTEGER,
        bildiren_personel_id INTEGER,
        sorumlu_personel_id INTEGER,
        hedef_tarih TEXT,
        anlik_aksiyon TEXT,
        kok_neden TEXT,
        kapatma_tarihi TEXT,
        kapanis_aciklamasi TEXT,
        kayit_zamani TEXT NOT NULL,
        guncelleme_zamani TEXT NOT NULL,
        FOREIGN KEY (depo_kabul_id)
            REFERENCES depo_kabul(id),
        FOREIGN KEY (uretim_id)
            REFERENCES uretim(id),
        FOREIGN KEY (paketleme_id)
            REFERENCES paketleme(id),
        FOREIGN KEY (sevkiyat_id)
            REFERENCES sevkiyat(id),
        FOREIGN KEY (tedarikci_id)
            REFERENCES tedarikciler(id),
        FOREIGN KEY (musteri_id)
            REFERENCES musteriler(id),
        FOREIGN KEY (bildiren_personel_id)
            REFERENCES personeller(id),
        FOREIGN KEY (sorumlu_personel_id)
            REFERENCES personeller(id)
    );

    CREATE TABLE IF NOT EXISTS kalite_capa_faaliyetleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uygunsuzluk_id INTEGER NOT NULL,
        faaliyet_turu TEXT NOT NULL CHECK(
            faaliyet_turu IN (
                'DUZELTME',
                'DUZELTICI',
                'ONLEYICI'
            )
        ),
        aciklama TEXT NOT NULL,
        sorumlu_personel_id INTEGER NOT NULL,
        hedef_tarih TEXT NOT NULL,
        durum TEXT NOT NULL DEFAULT 'ACIK' CHECK(
            durum IN (
                'ACIK',
                'DEVAM_EDIYOR',
                'TAMAMLANDI',
                'IPTAL'
            )
        ),
        tamamlanma_tarihi TEXT,
        tamamlanma_aciklamasi TEXT,
        etkinlik_durumu TEXT CHECK(
            etkinlik_durumu IN (
                'BEKLIYOR',
                'ETKILI',
                'ETKISIZ'
            )
        ),
        etkinlik_aciklamasi TEXT,
        dogrulayan_personel_id INTEGER,
        dogrulama_tarihi TEXT,
        kayit_zamani TEXT NOT NULL,
        guncelleme_zamani TEXT NOT NULL,
        FOREIGN KEY (uygunsuzluk_id)
            REFERENCES kalite_uygunsuzluklari(id)
            ON DELETE RESTRICT,
        FOREIGN KEY (sorumlu_personel_id)
            REFERENCES personeller(id),
        FOREIGN KEY (dogrulayan_personel_id)
            REFERENCES personeller(id)
    );

    CREATE INDEX IF NOT EXISTS
    idx_kalite_uygunsuzluk_durum
    ON kalite_uygunsuzluklari (
        durum,
        onem_derecesi
    );

    CREATE INDEX IF NOT EXISTS
    idx_kalite_uygunsuzluk_hedef
    ON kalite_uygunsuzluklari (
        hedef_tarih,
        durum
    );

    CREATE INDEX IF NOT EXISTS
    idx_kalite_uygunsuzluk_kaynak
    ON kalite_uygunsuzluklari (
        kaynak_turu,
        depo_kabul_id,
        uretim_id,
        paketleme_id,
        sevkiyat_id
    );

    CREATE INDEX IF NOT EXISTS
    idx_kalite_capa_uygunsuzluk
    ON kalite_capa_faaliyetleri (
        uygunsuzluk_id,
        durum
    );

    CREATE INDEX IF NOT EXISTS
    idx_kalite_capa_hedef
    ON kalite_capa_faaliyetleri (
        hedef_tarih,
        durum
    );
"""


MAMUL_MOVEMENT_TYPES = (
    "PAKETLEME",
    "SEVKIYAT",
    "TARIHSEL_KAPANIS",
    "IADE",
    "IMHA",
    "SAYIM_DUZELTME",
)


def _migration_1_mamul_movement_contract(conn):
    row = conn.execute("""
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'mamul_stok_hareketleri'
    """).fetchone()

    if row is None:
        raise RuntimeError(
            "Migration 1: mamul_stok_hareketleri "
            "tablosu bulunamadı."
        )

    current_sql = row[0] or ""

    if all(
        f"'{movement_type}'" in current_sql
        for movement_type in MAMUL_MOVEMENT_TYPES
    ):
        return

    conn.execute("""
        CREATE TABLE
        mamul_stok_hareketleri__migration_1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hareket_tarihi TEXT NOT NULL,
            paketleme_id INTEGER NOT NULL,
            hareket_tipi TEXT NOT NULL CHECK(
                hareket_tipi IN (
                    'PAKETLEME',
                    'SEVKIYAT',
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
        )
    """)

    conn.execute("""
        INSERT INTO
        mamul_stok_hareketleri__migration_1 (
            id,
            hareket_tarihi,
            paketleme_id,
            hareket_tipi,
            yon,
            paket_adedi,
            aciklama,
            kayit_zamani
        )
        SELECT
            id,
            hareket_tarihi,
            paketleme_id,
            hareket_tipi,
            yon,
            paket_adedi,
            aciklama,
            kayit_zamani
        FROM mamul_stok_hareketleri
    """)

    old_count = conn.execute("""
        SELECT COUNT(*)
        FROM mamul_stok_hareketleri
    """).fetchone()[0]

    new_count = conn.execute("""
        SELECT COUNT(*)
        FROM mamul_stok_hareketleri__migration_1
    """).fetchone()[0]

    if old_count != new_count:
        raise RuntimeError(
            "Migration 1 kayıt sayısı doğrulanamadı."
        )

    conn.execute("""
        DROP TABLE mamul_stok_hareketleri
    """)

    conn.execute("""
        ALTER TABLE
        mamul_stok_hareketleri__migration_1
        RENAME TO mamul_stok_hareketleri
    """)


def _migration_2_audit_trail(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS denetim_kayitlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            olay_zamani TEXT NOT NULL,
            kullanici_id INTEGER,
            personel_id INTEGER,
            kullanici_adi TEXT,
            ad_soyad TEXT,
            modul TEXT NOT NULL,
            islem TEXT NOT NULL,
            kayit_turu TEXT,
            kayit_id INTEGER,
            aciklama TEXT,
            eski_deger_json TEXT,
            yeni_deger_json TEXT,
            oturum_id TEXT
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_denetim_olay_zamani
        ON denetim_kayitlari (olay_zamani)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_denetim_modul_islem
        ON denetim_kayitlari (modul, islem)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_denetim_kayit
        ON denetim_kayitlari (kayit_turu, kayit_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_denetim_kullanici
        ON denetim_kayitlari (kullanici_id, olay_zamani)
    """)


def _migration_3_packaging_contract(conn):
    columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(paketleme)"
        ).fetchall()
    }

    if not columns:
        raise RuntimeError(
            "Migration 3: paketleme tablosu bulunamadı."
        )

    required_columns = (
        (
            "baslama_saati",
            "TEXT",
        ),
        (
            "bitis_saati",
            "TEXT",
        ),
        (
            "paketleme_suresi_dakika",
            "INTEGER",
        ),
        (
            "koli_ici_adet",
            "INTEGER",
        ),
    )

    for column_name, column_type in required_columns:
        if column_name in columns:
            continue

        conn.execute(
            f"ALTER TABLE paketleme "
            f"ADD COLUMN {column_name} {column_type}"
        )




def _migration_5_multi_product_foundation(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS urunler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            urun_kodu TEXT NOT NULL UNIQUE COLLATE NOCASE,
            urun_adi TEXT NOT NULL UNIQUE COLLATE NOCASE,
            kategori TEXT,
            barkod TEXT UNIQUE,
            birim TEXT NOT NULL DEFAULT 'KG',
            raf_omru_gun INTEGER,
            saklama_sicakligi TEXT,
            aktif INTEGER NOT NULL DEFAULT 1 CHECK(
                aktif IN (0, 1)
            ),
            aciklama TEXT,
            kayit_zamani TEXT NOT NULL
        )
    """)

    long_potato_exists = conn.execute("""
        SELECT id
        FROM urunler
        WHERE urun_kodu = ?
        LIMIT 1
    """, (
        "LP001",
    )).fetchone()

    if long_potato_exists is None:
        conn.execute("""
            INSERT INTO urunler (
                urun_kodu,
                urun_adi,
                kategori,
                birim,
                saklama_sicakligi,
                aktif,
                aciklama,
                kayit_zamani
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """, (
            "LP001",
            "Long Potato",
            "Dondurulmuş Patates Ürünü",
            "KG",
            "-18°C",
            (
                "REDBOX OS çok ürün altyapısı başlangıç "
                "ürünü"
            ),
            datetime.now().strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
        ))


def _migration_6_recipe_production_product_links(conn):
    product_row = conn.execute("""
        SELECT id
        FROM urunler
        WHERE urun_kodu = ?
        LIMIT 1
    """, (
        "LP001",
    )).fetchone()

    if product_row is None:
        raise RuntimeError(
            "Migration 6: LP001 Long Potato ürünü bulunamadı."
        )

    long_potato_id = product_row[0]

    recete_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(receteler)"
        ).fetchall()
    }

    if not recete_columns:
        raise RuntimeError(
            "Migration 6: receteler tablosu bulunamadı."
        )

    if "urun_id" not in recete_columns:
        conn.execute("""
            ALTER TABLE receteler
            ADD COLUMN urun_id INTEGER
            REFERENCES urunler(id)
        """)

    conn.execute("""
        UPDATE receteler
        SET urun_id = ?
        WHERE urun_id IS NULL
    """, (
        long_potato_id,
    ))

    production_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(uretim)"
        ).fetchall()
    }

    if not production_columns:
        raise RuntimeError(
            "Migration 6: uretim tablosu bulunamadı."
        )

    if "urun_id" not in production_columns:
        conn.execute("""
            ALTER TABLE uretim
            ADD COLUMN urun_id INTEGER
            REFERENCES urunler(id)
        """)

    conn.execute("""
        UPDATE uretim
        SET urun_id = ?
        WHERE urun_id IS NULL
    """, (
        long_potato_id,
    ))

    missing_recipe_links = conn.execute("""
        SELECT COUNT(*)
        FROM receteler
        WHERE urun_id IS NULL
    """).fetchone()[0]

    missing_production_links = conn.execute("""
        SELECT COUNT(*)
        FROM uretim
        WHERE urun_id IS NULL
    """).fetchone()[0]

    if missing_recipe_links:
        raise RuntimeError(
            "Migration 6: ürünsüz reçete kaydı kaldı."
        )

    if missing_production_links:
        raise RuntimeError(
            "Migration 6: ürünsüz üretim kaydı kaldı."
        )

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_receteler_urun_id
        ON receteler(urun_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_uretim_urun_id
        ON uretim(urun_id)
    """)


def _migration_7_packaging_shipment_product_links(conn):
    product_row = conn.execute("""
        SELECT id
        FROM urunler
        WHERE urun_kodu = ?
        LIMIT 1
    """, (
        "LP001",
    )).fetchone()

    if product_row is None:
        raise RuntimeError(
            "Migration 7: LP001 Long Potato ürünü bulunamadı."
        )

    long_potato_id = product_row[0]

    packaging_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(paketleme)"
        ).fetchall()
    }

    if not packaging_columns:
        raise RuntimeError(
            "Migration 7: paketleme tablosu bulunamadı."
        )

    if "urun_id" not in packaging_columns:
        conn.execute("""
            ALTER TABLE paketleme
            ADD COLUMN urun_id INTEGER
            REFERENCES urunler(id)
        """)

    conn.execute("""
        UPDATE paketleme
        SET urun_id = ?
        WHERE urun_id IS NULL
    """, (
        long_potato_id,
    ))

    shipment_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(sevkiyat)"
        ).fetchall()
    }

    if not shipment_columns:
        raise RuntimeError(
            "Migration 7: sevkiyat tablosu bulunamadı."
        )

    if "urun_id" not in shipment_columns:
        conn.execute("""
            ALTER TABLE sevkiyat
            ADD COLUMN urun_id INTEGER
            REFERENCES urunler(id)
        """)

    conn.execute("""
        UPDATE sevkiyat
        SET urun_id = ?
        WHERE urun_id IS NULL
    """, (
        long_potato_id,
    ))

    missing_packaging_links = conn.execute("""
        SELECT COUNT(*)
        FROM paketleme
        WHERE urun_id IS NULL
    """).fetchone()[0]

    missing_shipment_links = conn.execute("""
        SELECT COUNT(*)
        FROM sevkiyat
        WHERE urun_id IS NULL
    """).fetchone()[0]

    if missing_packaging_links:
        raise RuntimeError(
            "Migration 7: ürünsüz paketleme kaydı kaldı."
        )

    if missing_shipment_links:
        raise RuntimeError(
            "Migration 7: ürünsüz sevkiyat kaydı kaldı."
        )

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_paketleme_urun_id
        ON paketleme(urun_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_sevkiyat_urun_id
        ON sevkiyat(urun_id)
    """)

def _migration_4_quality_capa_foundation(conn):
    conn.executescript(
        QUALITY_CAPA_SCHEMA_SQL
    )


def _migration_8_product_recipe_active_contract(conn):
    missing_product_links = conn.execute("""
        SELECT COUNT(*)
        FROM receteler
        WHERE urun_id IS NULL
    """).fetchone()[0]

    if missing_product_links:
        raise RuntimeError(
            "Migration 8: ürünsüz reçete kaydı bulundu."
        )

    duplicate_active_products = conn.execute("""
        SELECT
            urun_id,
            COUNT(*)
        FROM receteler
        WHERE aktif = 1
        GROUP BY urun_id
        HAVING COUNT(*) > 1
    """).fetchall()

    if duplicate_active_products:
        raise RuntimeError(
            "Migration 8: aynı ürüne bağlı birden fazla "
            "aktif reçete bulundu."
        )

    conn.execute("""
        DROP INDEX IF EXISTS
        ux_receteler_tek_aktif
    """)

    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_receteler_urun_aktif
        ON receteler(urun_id)
        WHERE aktif = 1
    """)


def _migration_9_global_food_safety_foundation(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS kontrollu_dokumanlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dokuman_kodu TEXT NOT NULL UNIQUE COLLATE NOCASE,
            baslik TEXT NOT NULL,
            kategori TEXT NOT NULL,
            kapsam TEXT,
            dokuman_sahibi_personel_id INTEGER,
            gozden_gecirme_periyodu_ay INTEGER CHECK(
                gozden_gecirme_periyodu_ay IS NULL
                OR gozden_gecirme_periyodu_ay > 0
            ),
            aktif INTEGER NOT NULL DEFAULT 1 CHECK(
                aktif IN (0, 1)
            ),
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL,
            FOREIGN KEY (dokuman_sahibi_personel_id)
                REFERENCES personeller(id)
        );

        CREATE TABLE IF NOT EXISTS dokuman_revizyonlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dokuman_id INTEGER NOT NULL,
            revizyon_no TEXT NOT NULL,
            durum TEXT NOT NULL DEFAULT 'TASLAK' CHECK(
                durum IN (
                    'TASLAK',
                    'INCELEMEDE',
                    'ONAYLI',
                    'GERI_CEKILDI',
                    'ARSIV'
                )
            ),
            yayin_tarihi TEXT,
            gecerlilik_baslangic_tarihi TEXT,
            gecerlilik_bitis_tarihi TEXT,
            degisiklik_aciklamasi TEXT NOT NULL,
            icerik_ozeti TEXT,
            dosya_yolu TEXT,
            dosya_sha256 TEXT,
            olusturan_personel_id INTEGER NOT NULL,
            onaylayan_personel_id INTEGER,
            onay_zamani TEXT,
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL,
            FOREIGN KEY (dokuman_id)
                REFERENCES kontrollu_dokumanlar(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (olusturan_personel_id)
                REFERENCES personeller(id),
            FOREIGN KEY (onaylayan_personel_id)
                REFERENCES personeller(id),
            UNIQUE (dokuman_id, revizyon_no),
            CHECK (
                durum != 'ONAYLI'
                OR (
                    onaylayan_personel_id IS NOT NULL
                    AND onay_zamani IS NOT NULL
                    AND yayin_tarihi IS NOT NULL
                )
            )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_dokuman_tek_onayli_revizyon
        ON dokuman_revizyonlari(dokuman_id)
        WHERE durum = 'ONAYLI';

        CREATE INDEX IF NOT EXISTS
        idx_dokuman_revizyon_durum
        ON dokuman_revizyonlari (
            durum,
            gecerlilik_bitis_tarihi
        );

        CREATE INDEX IF NOT EXISTS
        idx_kontrollu_dokuman_kategori
        ON kontrollu_dokumanlar (
            kategori,
            aktif
        );

        CREATE TABLE IF NOT EXISTS dijital_onaylar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kaynak_turu TEXT NOT NULL,
            kaynak_id INTEGER NOT NULL,
            onay_turu TEXT NOT NULL,
            karar TEXT NOT NULL CHECK(
                karar IN (
                    'ONAYLANDI',
                    'REDDEDILDI',
                    'IADE_EDILDI',
                    'IPTAL_EDILDI'
                )
            ),
            kullanici_id INTEGER NOT NULL,
            personel_id INTEGER NOT NULL,
            kullanici_adi TEXT NOT NULL,
            ad_soyad TEXT NOT NULL,
            onay_zamani TEXT NOT NULL,
            aciklama TEXT,
            icerik_sha256 TEXT NOT NULL,
            oturum_id TEXT,
            FOREIGN KEY (kullanici_id)
                REFERENCES kullanici_hesaplari(id),
            FOREIGN KEY (personel_id)
                REFERENCES personeller(id)
        );

        CREATE INDEX IF NOT EXISTS
        idx_dijital_onay_kaynak
        ON dijital_onaylar (
            kaynak_turu,
            kaynak_id,
            onay_turu
        );

        CREATE INDEX IF NOT EXISTS
        idx_dijital_onay_personel
        ON dijital_onaylar (
            personel_id,
            onay_zamani
        );

        CREATE TABLE IF NOT EXISTS kanit_dosyalari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kaynak_turu TEXT NOT NULL,
            kaynak_id INTEGER NOT NULL,
            kanit_turu TEXT NOT NULL,
            dosya_adi TEXT NOT NULL,
            dosya_yolu TEXT NOT NULL,
            mime_turu TEXT,
            dosya_boyutu INTEGER CHECK(
                dosya_boyutu IS NULL
                OR dosya_boyutu >= 0
            ),
            dosya_sha256 TEXT NOT NULL,
            cekim_olay_zamani TEXT,
            aciklama TEXT,
            yukleyen_kullanici_id INTEGER,
            yukleyen_personel_id INTEGER,
            kayit_zamani TEXT NOT NULL,
            FOREIGN KEY (yukleyen_kullanici_id)
                REFERENCES kullanici_hesaplari(id),
            FOREIGN KEY (yukleyen_personel_id)
                REFERENCES personeller(id)
        );

        CREATE INDEX IF NOT EXISTS
        idx_kanit_dosyasi_kaynak
        ON kanit_dosyalari (
            kaynak_turu,
            kaynak_id
        );

        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_kanit_dosyasi_kaynak_hash
        ON kanit_dosyalari (
            kaynak_turu,
            kaynak_id,
            dosya_sha256
        );

        CREATE TABLE IF NOT EXISTS entegrasyon_cihazlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cihaz_kodu TEXT NOT NULL UNIQUE COLLATE NOCASE,
            cihaz_adi TEXT NOT NULL,
            cihaz_turu TEXT NOT NULL CHECK(
                cihaz_turu IN (
                    'SENSOR',
                    'KAMERA',
                    'MOBIL_CIHAZ',
                    'TERAZI',
                    'TERMOMETRE',
                    'DIGER'
                )
            ),
            konum TEXT,
            uretici TEXT,
            model TEXT,
            seri_no TEXT,
            yapilandirma_json TEXT CHECK(
                yapilandirma_json IS NULL
                OR json_valid(yapilandirma_json)
            ),
            son_gorulme_zamani TEXT,
            aktif INTEGER NOT NULL DEFAULT 1 CHECK(
                aktif IN (0, 1)
            ),
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS
        idx_entegrasyon_cihazi_tur_aktif
        ON entegrasyon_cihazlari (
            cihaz_turu,
            aktif
        );

        CREATE TABLE IF NOT EXISTS entegrasyon_olaylari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            olay_uuid TEXT NOT NULL UNIQUE,
            kaynak_turu TEXT NOT NULL CHECK(
                kaynak_turu IN (
                    'SENSOR',
                    'KAMERA',
                    'MOBIL',
                    'API',
                    'MANUEL'
                )
            ),
            cihaz_id INTEGER,
            olay_turu TEXT NOT NULL,
            olay_zamani TEXT NOT NULL,
            alinma_zamani TEXT NOT NULL,
            onem_derecesi TEXT NOT NULL DEFAULT 'BILGI' CHECK(
                onem_derecesi IN (
                    'BILGI',
                    'DUSUK',
                    'ORTA',
                    'YUKSEK',
                    'KRITIK'
                )
            ),
            konum TEXT,
            payload_json TEXT NOT NULL CHECK(
                json_valid(payload_json)
            ),
            durum TEXT NOT NULL DEFAULT 'YENI' CHECK(
                durum IN (
                    'YENI',
                    'INCELENIYOR',
                    'ISLENDI',
                    'YOK_SAYILDI',
                    'HATA'
                )
            ),
            kalite_uygunsuzluk_id INTEGER,
            isleyen_kullanici_id INTEGER,
            islenme_zamani TEXT,
            islem_aciklamasi TEXT,
            kayit_zamani TEXT NOT NULL,
            FOREIGN KEY (cihaz_id)
                REFERENCES entegrasyon_cihazlari(id),
            FOREIGN KEY (kalite_uygunsuzluk_id)
                REFERENCES kalite_uygunsuzluklari(id),
            FOREIGN KEY (isleyen_kullanici_id)
                REFERENCES kullanici_hesaplari(id)
        );

        CREATE INDEX IF NOT EXISTS
        idx_entegrasyon_olayi_durum
        ON entegrasyon_olaylari (
            durum,
            onem_derecesi,
            olay_zamani
        );

        CREATE INDEX IF NOT EXISTS
        idx_entegrasyon_olayi_cihaz
        ON entegrasyon_olaylari (
            cihaz_id,
            olay_zamani
        );

        CREATE INDEX IF NOT EXISTS
        idx_entegrasyon_olayi_uygunsuzluk
        ON entegrasyon_olaylari (
            kalite_uygunsuzluk_id
        );
    """)


def _migration_10_commercial_recipe_catalog_contract(conn):
    recipe_columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(receteler)"
        ).fetchall()
    }

    process_water_added = (
        "proses_suyu_kg" not in recipe_columns
    )

    if "recete_kodu" not in recipe_columns:
        conn.execute("""
            ALTER TABLE receteler
            ADD COLUMN recete_kodu TEXT
                COLLATE NOCASE
        """)

    if process_water_added:
        conn.execute("""
            ALTER TABLE receteler
            ADD COLUMN proses_suyu_kg REAL
                NOT NULL DEFAULT 0
                CHECK (proses_suyu_kg >= 0)
        """)

    if "durum" not in recipe_columns:
        conn.execute("""
            ALTER TABLE receteler
            ADD COLUMN durum TEXT
                NOT NULL DEFAULT 'TASLAK'
                CHECK (
                    durum IN (
                        'TASLAK',
                        'INCELEMEDE',
                        'ONAYLI',
                        'AKTIF',
                        'PASIF',
                        'ARSIV'
                    )
                )
        """)

    if "onaylayan_personel_id" not in recipe_columns:
        conn.execute("""
            ALTER TABLE receteler
            ADD COLUMN onaylayan_personel_id INTEGER
                REFERENCES personeller(id)
        """)

    if "onay_zamani" not in recipe_columns:
        conn.execute("""
            ALTER TABLE receteler
            ADD COLUMN onay_zamani TEXT
        """)

    if "icerik_sha256" not in recipe_columns:
        conn.execute("""
            ALTER TABLE receteler
            ADD COLUMN icerik_sha256 TEXT
        """)

    conn.execute("""
        UPDATE receteler
        SET recete_kodu = (
            SELECT
                UPPER(
                    REPLACE(
                        TRIM(u.urun_kodu),
                        ' ',
                        '-'
                    )
                ) || '-REC'
            FROM urunler AS u
            WHERE u.id = receteler.urun_id
        )
        WHERE recete_kodu IS NULL
           OR TRIM(recete_kodu) = ''
    """)

    if process_water_added:
        process_water_row = conn.execute("""
            SELECT deger
            FROM sistem_ayarlari
            WHERE anahtar = 'PARTI_PROSES_SUYU_KG'
            LIMIT 1
        """).fetchone()

        legacy_process_water = (
            float(process_water_row[0])
            if process_water_row is not None
            else 0.0
        )

        if legacy_process_water < 0:
            raise RuntimeError(
                "Migration 10: Eski proses suyu negatif olamaz."
            )

        conn.execute("""
            UPDATE receteler
            SET proses_suyu_kg = ?
        """, (
            legacy_process_water,
        ))

    conn.execute("""
        UPDATE receteler
        SET durum = CASE
            WHEN aktif = 1
                THEN 'AKTIF'
            WHEN EXISTS (
                SELECT 1
                FROM uretim_recete AS ur
                WHERE ur.recete_id = receteler.id
            )
                THEN 'ARSIV'
            ELSE 'PASIF'
        END
    """)

    invalid_rows = conn.execute("""
        SELECT
            r.id,
            r.recete_kodu,
            r.parti_teorik_kg,
            r.proses_suyu_kg,
            COALESCE(
                (
                    SELECT SUM(rk.miktar_kg)
                    FROM recete_kalemleri AS rk
                    WHERE rk.recete_id = r.id
                ),
                0
            ) AS hammadde_toplami
        FROM receteler AS r
        WHERE r.recete_kodu IS NULL
           OR TRIM(r.recete_kodu) = ''
           OR r.parti_teorik_kg <= 0
           OR r.proses_suyu_kg < 0
           OR ABS(
                r.parti_teorik_kg
                - (
                    r.proses_suyu_kg
                    + COALESCE(
                        (
                            SELECT SUM(rk.miktar_kg)
                            FROM recete_kalemleri AS rk
                            WHERE rk.recete_id = r.id
                        ),
                        0
                    )
                )
           ) >= 0.000001
    """).fetchall()

    if invalid_rows:
        raise RuntimeError(
            "Migration 10: Reçete katalog sözleşmesi "
            f"uyumsuz kayıtlar: {invalid_rows}"
        )

    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_receteler_catalog_revision
        ON receteler (
            urun_id,
            recete_kodu,
            revizyon_no
        )
        WHERE recete_kodu IS NOT NULL
          AND revizyon_no IS NOT NULL
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_receteler_catalog_status
        ON receteler (
            durum,
            aktif,
            gecerlilik_tarihi
        )
    """)


MIGRATIONS = (
    (
        1,
        "mamul_stock_movement_contract",
        _migration_1_mamul_movement_contract,
    ),
    (
        2,
        "professional_audit_trail",
        _migration_2_audit_trail,
    ),
    (
        3,
        "packaging_table_contract",
        _migration_3_packaging_contract,
    ),
    (
        4,
        "quality_capa_foundation",
        _migration_4_quality_capa_foundation,
    ),
    (
        5,
        "multi_product_foundation",
        _migration_5_multi_product_foundation,
    ),
    (
        6,
        "recipe_production_product_links",
        _migration_6_recipe_production_product_links,
    ),
    (
        7,
        "packaging_shipment_product_links",
        _migration_7_packaging_shipment_product_links,
    ),
    (
        8,
        "product_recipe_active_contract",
        _migration_8_product_recipe_active_contract,
    ),
    (
        9,
        "global_food_safety_foundation",
        _migration_9_global_food_safety_foundation,
    ),
    (
        10,
        "commercial_recipe_catalog_contract",
        _migration_10_commercial_recipe_catalog_contract,
    ),
)


def run_migrations(database_path):
    database_path = Path(database_path)

    if not database_path.exists():
        raise FileNotFoundError(
            f"Migration DB bulunamadı: {database_path}"
        )

    conn = sqlite3.connect(database_path)

    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN IMMEDIATE")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS
            schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL
            )
        """)

        current_version = conn.execute(
            "PRAGMA user_version"
        ).fetchone()[0]

        if current_version > LATEST_SCHEMA_VERSION:
            raise RuntimeError(
                "Veritabanı şema sürümü uygulamadan yeni: "
                f"{current_version} > {LATEST_SCHEMA_VERSION}"
            )

        applied_versions = {
            row[0]
            for row in conn.execute("""
                SELECT version
                FROM schema_migrations
            """).fetchall()
        }

        for version, name, migration in MIGRATIONS:
            if version in applied_versions:
                continue

            migration(conn)

            conn.execute("""
                INSERT INTO schema_migrations (
                    version,
                    name,
                    applied_at
                )
                VALUES (?, ?, ?)
            """, (
                version,
                name,
                datetime.now().strftime(
                    "%d.%m.%Y %H:%M:%S"
                ),
            ))

        conn.execute(
            f"PRAGMA user_version = "
            f"{LATEST_SCHEMA_VERSION}"
        )
        conn.commit()

        conn.execute("PRAGMA foreign_keys = ON")

        violations = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise RuntimeError(
                "Migration sonrası foreign key ihlali: "
                f"{violations}"
            )

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(
                "Migration sonrası integrity hatası: "
                f"{integrity}"
            )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

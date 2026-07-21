import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


LATEST_SCHEMA_VERSION = 15


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

    legacy_data_exists = any(
        conn.execute(
            f"SELECT 1 FROM {table} LIMIT 1"
        ).fetchone()
        is not None
        for table in (
            "receteler",
            "uretim",
            "paketleme",
            "sevkiyat",
        )
    )

    if not legacy_data_exists:
        return

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
                "REDBOX OS tarihsel veri geçişi "
                "bağlama ürünü"
            ),
            datetime.now().strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
        ))




def _migration_6_recipe_production_product_links(conn):
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

    if missing_recipe_links or missing_production_links:
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
                "Migration 6: tarihsel kayıtlar için "
                "LP001 bağlama ürünü bulunamadı."
            )

        product_id = product_row[0]

        conn.execute("""
            UPDATE receteler
            SET urun_id = ?
            WHERE urun_id IS NULL
        """, (product_id,))

        conn.execute("""
            UPDATE uretim
            SET urun_id = ?
            WHERE urun_id IS NULL
        """, (product_id,))

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

    if missing_packaging_links or missing_shipment_links:
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
                "Migration 7: tarihsel kayıtlar için "
                "LP001 bağlama ürünü bulunamadı."
            )

        product_id = product_row[0]

        conn.execute("""
            UPDATE paketleme
            SET urun_id = ?
            WHERE urun_id IS NULL
        """, (product_id,))

        conn.execute("""
            UPDATE sevkiyat
            SET urun_id = ?
            WHERE urun_id IS NULL
        """, (product_id,))

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


def _migration_11_company_first_setup_foundation(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS firma_profili (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            ticari_unvan TEXT NOT NULL,
            kisa_ad TEXT NOT NULL,
            vergi_dairesi TEXT,
            vergi_no TEXT,
            ulke TEXT NOT NULL DEFAULT 'Türkiye',
            il TEXT,
            ilce TEXT,
            adres TEXT,
            telefon TEXT,
            eposta TEXT,
            aktif INTEGER NOT NULL DEFAULT 1
                CHECK (aktif IN (0, 1)),
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT
        );

        CREATE TABLE IF NOT EXISTS tesis_profilleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firma_id INTEGER NOT NULL,
            tesis_kodu TEXT NOT NULL UNIQUE COLLATE NOCASE,
            tesis_adi TEXT NOT NULL,
            tesis_turu TEXT NOT NULL DEFAULT 'URETIM'
                CHECK (
                    tesis_turu IN (
                        'URETIM',
                        'DEPO',
                        'MERKEZ',
                        'DIGER'
                    )
                ),
            ulke TEXT NOT NULL DEFAULT 'Türkiye',
            il TEXT,
            ilce TEXT,
            adres TEXT,
            telefon TEXT,
            eposta TEXT,
            ana_tesis INTEGER NOT NULL DEFAULT 0
                CHECK (ana_tesis IN (0, 1)),
            aktif INTEGER NOT NULL DEFAULT 1
                CHECK (aktif IN (0, 1)),
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT,
            FOREIGN KEY (firma_id)
                REFERENCES firma_profili(id)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_tesis_profilleri_ana_tesis
        ON tesis_profilleri (firma_id)
        WHERE ana_tesis = 1 AND aktif = 1;

        CREATE TABLE IF NOT EXISTS ilk_kurulum_durumu (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            kullanim_modu TEXT NOT NULL
                CHECK (kullanim_modu IN ('GERCEK', 'DEMO')),
            tamamlandi INTEGER NOT NULL DEFAULT 0
                CHECK (tamamlandi IN (0, 1)),
            firma_id INTEGER,
            tesis_id INTEGER,
            ilk_yonetici_hesap_id INTEGER,
            baslama_zamani TEXT NOT NULL,
            tamamlanma_zamani TEXT,
            kurulum_surumu INTEGER NOT NULL DEFAULT 1
                CHECK (kurulum_surumu >= 1),
            FOREIGN KEY (firma_id)
                REFERENCES firma_profili(id),
            FOREIGN KEY (tesis_id)
                REFERENCES tesis_profilleri(id),
            FOREIGN KEY (ilk_yonetici_hesap_id)
                REFERENCES kullanici_hesaplari(id),
            CHECK (
                tamamlandi = 0
                OR (
                    firma_id IS NOT NULL
                    AND tesis_id IS NOT NULL
                    AND ilk_yonetici_hesap_id IS NOT NULL
                    AND tamamlanma_zamani IS NOT NULL
                )
            )
        );
    """)




def _migration_12_licensing_foundation(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS lisans_kayitlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lisans_uuid TEXT NOT NULL UNIQUE,
            lisans_anahtari_sha256 TEXT NOT NULL UNIQUE
                CHECK (LENGTH(lisans_anahtari_sha256) = 64),
            firma_id INTEGER NOT NULL,
            cihaz_parmak_izi_sha256 TEXT NOT NULL
                CHECK (
                    LENGTH(cihaz_parmak_izi_sha256) = 64
                ),
            urun_kodu TEXT NOT NULL DEFAULT 'REDBOX_OS'
                CHECK (urun_kodu = 'REDBOX_OS'),
            lisans_turu TEXT NOT NULL
                CHECK (
                    lisans_turu IN (
                        'SURELI',
                        'SURESIZ'
                    )
                ),
            durum TEXT NOT NULL DEFAULT 'AKTIF'
                CHECK (
                    durum IN (
                        'AKTIF',
                        'GRACE',
                        'ASKIDA',
                        'IPTAL',
                        'SURESI_DOLDU'
                    )
                ),
            baslangic_tarihi TEXT NOT NULL,
            bitis_tarihi TEXT,
            grace_period_gun INTEGER NOT NULL DEFAULT 7
                CHECK (
                    grace_period_gun BETWEEN 0 AND 30
                ),
            lisans_surumu INTEGER NOT NULL DEFAULT 1
                CHECK (lisans_surumu >= 1),
            imzali_payload_json TEXT NOT NULL
                CHECK (json_valid(imzali_payload_json)),
            imza_base64 TEXT NOT NULL,
            acik_anahtar_kimligi TEXT NOT NULL,
            aktivasyon_zamani TEXT NOT NULL,
            son_dogrulama_zamani TEXT,
            son_basarili_dogrulama_zamani TEXT,
            son_guvenilir_zaman TEXT,
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL,
            FOREIGN KEY (firma_id)
                REFERENCES firma_profili(id),
            CHECK (
                (
                    lisans_turu = 'SURELI'
                    AND bitis_tarihi IS NOT NULL
                )
                OR (
                    lisans_turu = 'SURESIZ'
                    AND bitis_tarihi IS NULL
                )
            )
        );

        CREATE UNIQUE INDEX IF NOT EXISTS
        ux_lisans_kayitlari_aktif_firma
        ON lisans_kayitlari (firma_id)
        WHERE durum IN ('AKTIF', 'GRACE');

        CREATE INDEX IF NOT EXISTS
        idx_lisans_kayitlari_cihaz
        ON lisans_kayitlari (
            cihaz_parmak_izi_sha256,
            durum
        );

        CREATE TABLE IF NOT EXISTS lisans_gecis_durumu (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            durum TEXT NOT NULL DEFAULT 'AKTIF'
                CHECK (
                    durum IN (
                        'AKTIF',
                        'TAMAMLANDI',
                        'SONA_ERDI'
                    )
                ),
            kaynak TEXT NOT NULL
                CHECK (
                    kaynak IN (
                        'LEGACY_UPGRADE'
                    )
                ),
            baslangic_zamani TEXT NOT NULL,
            bitis_zamani TEXT NOT NULL,
            gecis_suresi_gun INTEGER NOT NULL DEFAULT 30
                CHECK (gecis_suresi_gun = 30),
            tamamlanma_zamani TEXT,
            kayit_zamani TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS lisans_dogrulama_kayitlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lisans_id INTEGER,
            kontrol_zamani TEXT NOT NULL,
            sonuc TEXT NOT NULL
                CHECK (
                    sonuc IN (
                        'BASARILI',
                        'BASARISIZ',
                        'GRACE'
                    )
                ),
            kaynak TEXT NOT NULL
                CHECK (
                    kaynak IN (
                        'AKTIVASYON',
                        'BASLANGIC',
                        'PERIYODIK',
                        'MANUEL'
                    )
                ),
            neden_kodu TEXT NOT NULL,
            aciklama TEXT,
            cihaz_parmak_izi_sha256 TEXT
                CHECK (
                    cihaz_parmak_izi_sha256 IS NULL
                    OR LENGTH(cihaz_parmak_izi_sha256) = 64
                ),
            cevrimdisi INTEGER NOT NULL DEFAULT 1
                CHECK (cevrimdisi IN (0, 1)),
            oturum_id TEXT,
            FOREIGN KEY (lisans_id)
                REFERENCES lisans_kayitlari(id)
        );

        CREATE INDEX IF NOT EXISTS
        idx_lisans_dogrulama_lisans_zaman
        ON lisans_dogrulama_kayitlari (
            lisans_id,
            kontrol_zamani
        );

        CREATE INDEX IF NOT EXISTS
        idx_lisans_dogrulama_sonuc_zaman
        ON lisans_dogrulama_kayitlari (
            sonuc,
            kontrol_zamani
        );
    """)

    account_table_exists = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'kullanici_hesaplari'
        LIMIT 1
        """
    ).fetchone() is not None

    active_accounts = 0

    if account_table_exists:
        active_accounts = conn.execute("""
            SELECT COUNT(*)
            FROM kullanici_hesaplari
            WHERE aktif = 1
        """).fetchone()[0]

    existing_transition = conn.execute("""
        SELECT id
        FROM lisans_gecis_durumu
        WHERE id = 1
    """).fetchone()

    if active_accounts > 0 and existing_transition is None:
        start_time = datetime.now().astimezone()
        end_time = start_time + timedelta(days=30)
        timestamp = start_time.isoformat()

        conn.execute("""
            INSERT INTO lisans_gecis_durumu (
                id,
                durum,
                kaynak,
                baslangic_zamani,
                bitis_zamani,
                gecis_suresi_gun,
                kayit_zamani
            )
            VALUES (
                1,
                'AKTIF',
                'LEGACY_UPGRADE',
                ?,
                ?,
                30,
                ?
            )
        """, (
            timestamp,
            end_time.isoformat(),
            timestamp,
        ))


def _migration_13_backup_recovery_foundation(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS yedekleme_politikasi (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            aktif INTEGER NOT NULL DEFAULT 1
                CHECK (aktif IN (0, 1)),
            siklik_saat INTEGER NOT NULL DEFAULT 24
                CHECK (
                    siklik_saat BETWEEN 1 AND 168
                ),
            saklama_adedi INTEGER NOT NULL DEFAULT 14
                CHECK (
                    saklama_adedi BETWEEN 1 AND 100
                ),
            son_otomatik_yedek_zamani TEXT,
            sonraki_otomatik_yedek_zamani TEXT,
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS yedekleme_kayitlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            yedek_uuid TEXT NOT NULL UNIQUE,
            yedek_turu TEXT NOT NULL
                CHECK (
                    yedek_turu IN (
                        'MANUEL',
                        'OTOMATIK',
                        'GERI_YUKLEME_ONCESI'
                    )
                ),
            dosya_adi TEXT NOT NULL,
            manifest_dosya_adi TEXT NOT NULL,
            database_sha256 TEXT NOT NULL
                CHECK (
                    LENGTH(database_sha256) = 64
                ),
            boyut_byte INTEGER NOT NULL
                CHECK (boyut_byte > 0),
            schema_version INTEGER NOT NULL
                CHECK (schema_version >= 1),
            durum TEXT NOT NULL DEFAULT 'BASARILI'
                CHECK (
                    durum IN (
                        'BASARILI',
                        'SILINDI'
                    )
                ),
            olusturma_zamani TEXT NOT NULL,
            dogrulama_zamani TEXT NOT NULL,
            silinme_zamani TEXT,
            kullanici_id INTEGER,
            oturum_id TEXT,
            FOREIGN KEY (kullanici_id)
                REFERENCES kullanici_hesaplari(id)
        );

        CREATE INDEX IF NOT EXISTS
        idx_yedekleme_kayit_tur_zaman
        ON yedekleme_kayitlari (
            yedek_turu,
            olusturma_zamani
        );

        CREATE INDEX IF NOT EXISTS
        idx_yedekleme_kayit_durum_zaman
        ON yedekleme_kayitlari (
            durum,
            olusturma_zamani
        );

        CREATE TABLE IF NOT EXISTS geri_yukleme_kayitlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            geri_yukleme_uuid TEXT NOT NULL UNIQUE,
            kaynak_dosya_adi TEXT NOT NULL,
            kaynak_sha256 TEXT NOT NULL
                CHECK (
                    LENGTH(kaynak_sha256) = 64
                ),
            emniyet_yedegi_dosya_adi TEXT NOT NULL,
            emniyet_yedegi_sha256 TEXT NOT NULL
                CHECK (
                    LENGTH(emniyet_yedegi_sha256) = 64
                ),
            onceki_schema_version INTEGER NOT NULL,
            sonraki_schema_version INTEGER,
            durum TEXT NOT NULL
                CHECK (
                    durum IN (
                        'HAZIRLANDI',
                        'TAMAMLANDI',
                        'GERI_ALINDI'
                    )
                ),
            baslangic_zamani TEXT NOT NULL,
            tamamlanma_zamani TEXT,
            kullanici_id INTEGER,
            oturum_id TEXT,
            FOREIGN KEY (kullanici_id)
                REFERENCES kullanici_hesaplari(id)
        );

        CREATE INDEX IF NOT EXISTS
        idx_geri_yukleme_durum_zaman
        ON geri_yukleme_kayitlari (
            durum,
            baslangic_zamani
        );
    """)

    now = datetime.now().astimezone().isoformat()

    conn.execute("""
        INSERT OR IGNORE INTO yedekleme_politikasi (
            id,
            aktif,
            siklik_saat,
            saklama_adedi,
            kayit_zamani,
            guncelleme_zamani
        )
        VALUES (
            1,
            1,
            24,
            14,
            ?,
            ?
        )
    """, (now, now))


def _migration_14_haccp_engine(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS haccp_planlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_kodu TEXT NOT NULL UNIQUE,
            urun_id INTEGER NOT NULL,
            ad TEXT NOT NULL,
            urun_aciklamasi TEXT NOT NULL,
            amaclanan_kullanim TEXT NOT NULL,
            hedef_tuketici TEXT,
            kullanim_kisitlari TEXT,
            revizyon_no INTEGER NOT NULL DEFAULT 1
                CHECK (revizyon_no >= 1),
            durum TEXT NOT NULL DEFAULT 'TASLAK'
                CHECK (
                    durum IN (
                        'TASLAK',
                        'INCELEMEDE',
                        'ONAYLI',
                        'ARSIV'
                    )
                ),
            onceki_plan_id INTEGER,
            hazirlayan_personel_id INTEGER,
            onaylayan_personel_id INTEGER,
            onay_zamani TEXT,
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL,
            FOREIGN KEY (urun_id)
                REFERENCES urunler(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (onceki_plan_id)
                REFERENCES haccp_planlari(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (hazirlayan_personel_id)
                REFERENCES personeller(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (onaylayan_personel_id)
                REFERENCES personeller(id)
                ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS haccp_proses_adimlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            adim_no INTEGER NOT NULL
                CHECK (adim_no >= 1),
            ad TEXT NOT NULL,
            aciklama TEXT,
            girdiler TEXT,
            ciktilar TEXT,
            sorumlu_rol TEXT,
            yerinde_dogrulandi INTEGER NOT NULL DEFAULT 0
                CHECK (yerinde_dogrulandi IN (0, 1)),
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL,
            UNIQUE (plan_id, adim_no),
            FOREIGN KEY (plan_id)
                REFERENCES haccp_planlari(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS haccp_akis_dogrulamalari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            dogrulama_tarihi TEXT NOT NULL,
            dogrulayan_personel_id INTEGER NOT NULL,
            sonuc TEXT NOT NULL
                CHECK (
                    sonuc IN (
                        'UYGUN',
                        'UYGUN_DEGIL'
                    )
                ),
            bulgular TEXT,
            aksiyonlar TEXT,
            kayit_zamani TEXT NOT NULL,
            FOREIGN KEY (plan_id)
                REFERENCES haccp_planlari(id)
                ON DELETE CASCADE,
            FOREIGN KEY (dogrulayan_personel_id)
                REFERENCES personeller(id)
                ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS haccp_tehlikeleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tehlike_kodu TEXT NOT NULL UNIQUE,
            ad TEXT NOT NULL,
            tehlike_turu TEXT NOT NULL
                CHECK (
                    tehlike_turu IN (
                        'BIYOLOJIK',
                        'KIMYASAL',
                        'FIZIKSEL',
                        'ALERJEN'
                    )
                ),
            aciklama TEXT NOT NULL,
            kaynak TEXT,
            aktif INTEGER NOT NULL DEFAULT 1
                CHECK (aktif IN (0, 1)),
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS
        haccp_tehlike_degerlendirmeleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            proses_adimi_id INTEGER NOT NULL,
            tehlike_id INTEGER NOT NULL,
            olasilik INTEGER NOT NULL
                CHECK (olasilik BETWEEN 1 AND 5),
            siddet INTEGER NOT NULL
                CHECK (siddet BETWEEN 1 AND 5),
            risk_puani INTEGER NOT NULL
                CHECK (
                    risk_puani = olasilik * siddet
                    AND risk_puani BETWEEN 1 AND 25
                ),
            onemli_tehlike INTEGER NOT NULL
                CHECK (onemli_tehlike IN (0, 1)),
            gerekce TEXT NOT NULL,
            kontrol_onlemleri TEXT NOT NULL,
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL,
            UNIQUE (
                plan_id,
                proses_adimi_id,
                tehlike_id
            ),
            FOREIGN KEY (plan_id)
                REFERENCES haccp_planlari(id)
                ON DELETE CASCADE,
            FOREIGN KEY (proses_adimi_id)
                REFERENCES haccp_proses_adimlari(id)
                ON DELETE CASCADE,
            FOREIGN KEY (tehlike_id)
                REFERENCES haccp_tehlikeleri(id)
                ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS haccp_kontrol_noktalari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            degerlendirme_id INTEGER NOT NULL UNIQUE,
            kontrol_kodu TEXT NOT NULL UNIQUE,
            sinif TEXT NOT NULL
                CHECK (
                    sinif IN (
                        'CCP',
                        'OPRP',
                        'PRP'
                    )
                ),
            karar_agaci_cevaplari TEXT,
            karar_gerekcesi TEXT NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1
                CHECK (aktif IN (0, 1)),
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL,
            FOREIGN KEY (degerlendirme_id)
                REFERENCES
                    haccp_tehlike_degerlendirmeleri(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS haccp_kritik_limitleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kontrol_noktasi_id INTEGER NOT NULL,
            parametre TEXT NOT NULL,
            operator TEXT NOT NULL
                CHECK (
                    operator IN (
                        'MIN',
                        'MAX',
                        'ARALIK',
                        'ESIT',
                        'NITEL'
                    )
                ),
            alt_limit REAL,
            ust_limit REAL,
            hedef_deger TEXT,
            birim TEXT,
            bilimsel_dayanak TEXT NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1
                CHECK (aktif IN (0, 1)),
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL,
            FOREIGN KEY (kontrol_noktasi_id)
                REFERENCES haccp_kontrol_noktalari(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS haccp_izleme_planlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kontrol_noktasi_id INTEGER NOT NULL,
            izlenecek_parametre TEXT NOT NULL,
            yontem TEXT NOT NULL,
            siklik TEXT NOT NULL,
            sorumlu_rol TEXT NOT NULL,
            kayit_formu TEXT NOT NULL,
            sapmada_yapilacaklar TEXT NOT NULL,
            aktif INTEGER NOT NULL DEFAULT 1
                CHECK (aktif IN (0, 1)),
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL,
            FOREIGN KEY (kontrol_noktasi_id)
                REFERENCES haccp_kontrol_noktalari(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS haccp_sapmalari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kontrol_noktasi_id INTEGER NOT NULL,
            tespit_zamani TEXT NOT NULL,
            tespit_degeri TEXT,
            aciklama TEXT NOT NULL,
            urun_karari TEXT NOT NULL,
            duzeltme TEXT NOT NULL,
            kok_neden TEXT,
            kalite_uygunsuzluk_id INTEGER,
            sorumlu_personel_id INTEGER,
            durum TEXT NOT NULL DEFAULT 'ACIK'
                CHECK (
                    durum IN (
                        'ACIK',
                        'INCELEMEDE',
                        'CAPA',
                        'KAPALI'
                    )
                ),
            kapanis_zamani TEXT,
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL,
            FOREIGN KEY (kontrol_noktasi_id)
                REFERENCES haccp_kontrol_noktalari(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (kalite_uygunsuzluk_id)
                REFERENCES kalite_uygunsuzluklari(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (sorumlu_personel_id)
                REFERENCES personeller(id)
                ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS haccp_dogrulamalari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            dogrulama_turu TEXT NOT NULL
                CHECK (
                    dogrulama_turu IN (
                        'PLAN',
                        'AKIS',
                        'IZLEME',
                        'KALIBRASYON',
                        'IC_DENETIM'
                    )
                ),
            dogrulama_tarihi TEXT NOT NULL,
            dogrulayan_personel_id INTEGER NOT NULL,
            sonuc TEXT NOT NULL
                CHECK (
                    sonuc IN (
                        'UYGUN',
                        'UYGUN_DEGIL'
                    )
                ),
            bulgular TEXT,
            aksiyonlar TEXT,
            sonraki_dogrulama_tarihi TEXT,
            kayit_zamani TEXT NOT NULL,
            guncelleme_zamani TEXT NOT NULL,
            FOREIGN KEY (plan_id)
                REFERENCES haccp_planlari(id)
                ON DELETE CASCADE,
            FOREIGN KEY (dogrulayan_personel_id)
                REFERENCES personeller(id)
                ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS
        idx_haccp_plan_urun_durum
        ON haccp_planlari (
            urun_id,
            durum
        );

        CREATE INDEX IF NOT EXISTS
        idx_haccp_proses_plan_sira
        ON haccp_proses_adimlari (
            plan_id,
            adim_no
        );

        CREATE INDEX IF NOT EXISTS
        idx_haccp_tehlike_adim_tur
        ON haccp_tehlike_degerlendirmeleri (
            proses_adimi_id,
            tehlike_id
        );

        CREATE INDEX IF NOT EXISTS
        idx_haccp_degerlendirme_risk
        ON haccp_tehlike_degerlendirmeleri (
            risk_puani,
            onemli_tehlike
        );

        CREATE INDEX IF NOT EXISTS
        idx_haccp_kontrol_sinif
        ON haccp_kontrol_noktalari (
            sinif,
            aktif
        );

        CREATE INDEX IF NOT EXISTS
        idx_haccp_izleme_kontrol
        ON haccp_izleme_planlari (
            kontrol_noktasi_id,
            aktif
        );

        CREATE INDEX IF NOT EXISTS
        idx_haccp_sapma_durum
        ON haccp_sapmalari (
            durum,
            tespit_zamani
        );

        CREATE INDEX IF NOT EXISTS
        idx_haccp_dogrulama_plan_tarih
        ON haccp_dogrulamalari (
            plan_id,
            dogrulama_tarihi
        );
    """)


def _migration_15_prerequisite_programs(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS prp_programlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_kodu TEXT NOT NULL UNIQUE,
            program_turu TEXT NOT NULL CHECK (
                program_turu IN (
                    'ALERJEN',
                    'KALIBRASYON',
                    'BAKIM_ARIZA',
                    'ZARARLI_MUCADELESI',
                    'EGITIM_YETKINLIK',
                    'TACCP',
                    'VACCP'
                )
            ),
            baslik TEXT NOT NULL,
            kapsam TEXT,
            sorumlu_personel_id INTEGER,
            baslangic_tarihi TEXT,
            gozden_gecirme_tarihi TEXT,
            durum TEXT NOT NULL DEFAULT 'TASLAK' CHECK (
                durum IN (
                    'TASLAK',
                    'AKTIF',
                    'ASKIDA',
                    'ARSIV'
                )
            ),
            versiyon INTEGER NOT NULL DEFAULT 1 CHECK (
                versiyon > 0
            ),
            olusturma_zamani TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            guncelleme_zamani TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sorumlu_personel_id)
                REFERENCES personeller(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS prp_kayitlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_id INTEGER NOT NULL,
            kayit_turu TEXT NOT NULL,
            kayit_tarihi TEXT NOT NULL,
            baslik TEXT NOT NULL,
            aciklama TEXT,
            sonuc TEXT,
            uygunsuzluk_var INTEGER NOT NULL DEFAULT 0 CHECK (
                uygunsuzluk_var IN (0, 1)
            ),
            sorumlu_personel_id INTEGER,
            kanit_referansi TEXT,
            olusturma_zamani TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (program_id)
                REFERENCES prp_programlari(id)
                ON DELETE CASCADE,
            FOREIGN KEY (sorumlu_personel_id)
                REFERENCES personeller(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS prp_aksiyonlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kayit_id INTEGER NOT NULL,
            aksiyon TEXT NOT NULL,
            sorumlu_personel_id INTEGER,
            hedef_tarih TEXT,
            tamamlanma_tarihi TEXT,
            durum TEXT NOT NULL DEFAULT 'ACIK' CHECK (
                durum IN (
                    'ACIK',
                    'DEVAM_EDIYOR',
                    'DOGRULAMADA',
                    'KAPALI',
                    'IPTAL'
                )
            ),
            etkinlik_sonucu TEXT,
            olusturma_zamani TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kayit_id)
                REFERENCES prp_kayitlari(id)
                ON DELETE CASCADE,
            FOREIGN KEY (sorumlu_personel_id)
                REFERENCES personeller(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS prp_alerjen_matrisi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_id INTEGER NOT NULL,
            urun_id INTEGER,
            alerjen_kodu TEXT NOT NULL,
            icerir INTEGER NOT NULL DEFAULT 0 CHECK (
                icerir IN (0, 1)
            ),
            capraz_bulasma_riski INTEGER NOT NULL DEFAULT 0 CHECK (
                capraz_bulasma_riski IN (0, 1)
            ),
            kontrol_onlemi TEXT,
            etiket_beyani TEXT,
            UNIQUE (program_id, urun_id, alerjen_kodu),
            FOREIGN KEY (program_id)
                REFERENCES prp_programlari(id)
                ON DELETE CASCADE,
            FOREIGN KEY (urun_id)
                REFERENCES urunler(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS prp_ekipmanlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_id INTEGER NOT NULL,
            ekipman_kodu TEXT NOT NULL,
            ekipman_adi TEXT NOT NULL,
            ekipman_turu TEXT NOT NULL CHECK (
                ekipman_turu IN (
                    'OLCUM',
                    'URETIM',
                    'DEPOLAMA',
                    'DIGER'
                )
            ),
            konum TEXT,
            son_islem_tarihi TEXT,
            sonraki_islem_tarihi TEXT,
            durum TEXT NOT NULL DEFAULT 'AKTIF' CHECK (
                durum IN (
                    'AKTIF',
                    'BAKIMDA',
                    'ARIZALI',
                    'KULLANIM_DISI'
                )
            ),
            UNIQUE (program_id, ekipman_kodu),
            FOREIGN KEY (program_id)
                REFERENCES prp_programlari(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS prp_egitim_katilimlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_id INTEGER NOT NULL,
            personel_id INTEGER NOT NULL,
            egitim_kodu TEXT NOT NULL,
            egitim_adi TEXT NOT NULL,
            egitim_tarihi TEXT NOT NULL,
            gecerlilik_tarihi TEXT,
            puan REAL,
            yetkin INTEGER NOT NULL DEFAULT 0 CHECK (
                yetkin IN (0, 1)
            ),
            UNIQUE (
                program_id,
                personel_id,
                egitim_kodu,
                egitim_tarihi
            ),
            FOREIGN KEY (program_id)
                REFERENCES prp_programlari(id)
                ON DELETE CASCADE,
            FOREIGN KEY (personel_id)
                REFERENCES personeller(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS prp_risk_degerlendirmeleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_id INTEGER NOT NULL,
            risk_turu TEXT NOT NULL CHECK (
                risk_turu IN ('TACCP', 'VACCP')
            ),
            varlik_veya_surec TEXT NOT NULL,
            tehdit_veya_zafiyet TEXT NOT NULL,
            olasilik INTEGER NOT NULL CHECK (
                olasilik BETWEEN 1 AND 5
            ),
            etki INTEGER NOT NULL CHECK (
                etki BETWEEN 1 AND 5
            ),
            risk_puani INTEGER NOT NULL CHECK (
                risk_puani BETWEEN 1 AND 25
            ),
            kontrol_onlemleri TEXT,
            kalan_risk INTEGER CHECK (
                kalan_risk BETWEEN 1 AND 25
            ),
            durum TEXT NOT NULL DEFAULT 'ACIK' CHECK (
                durum IN ('ACIK', 'KONTROL_ALTINDA', 'KAPALI')
            ),
            gozden_gecirme_tarihi TEXT,
            FOREIGN KEY (program_id)
                REFERENCES prp_programlari(id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_prp_program_tur_durum
            ON prp_programlari(program_turu, durum);

        CREATE INDEX IF NOT EXISTS idx_prp_kayit_program_tarih
            ON prp_kayitlari(program_id, kayit_tarihi);

        CREATE INDEX IF NOT EXISTS idx_prp_aksiyon_kayit_durum
            ON prp_aksiyonlari(kayit_id, durum);

        CREATE INDEX IF NOT EXISTS idx_prp_alerjen_urun
            ON prp_alerjen_matrisi(urun_id, alerjen_kodu);

        CREATE INDEX IF NOT EXISTS idx_prp_ekipman_tur_durum
            ON prp_ekipmanlari(ekipman_turu, durum);

        CREATE INDEX IF NOT EXISTS idx_prp_egitim_personel
            ON prp_egitim_katilimlari(personel_id, gecerlilik_tarihi);

        CREATE INDEX IF NOT EXISTS idx_prp_risk_tur_durum
            ON prp_risk_degerlendirmeleri(risk_turu, durum);
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
    (
        11,
        "company_first_setup_foundation",
        _migration_11_company_first_setup_foundation,
    ),
    (
        12,
        "licensing_foundation",
        _migration_12_licensing_foundation,
    ),
    (
        13,
        "backup_recovery_foundation",
        _migration_13_backup_recovery_foundation,
    ),
    (
        14,
        "haccp_engine",
        _migration_14_haccp_engine,
    ),
    (
        15,
        "prerequisite_programs",
        _migration_15_prerequisite_programs,
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

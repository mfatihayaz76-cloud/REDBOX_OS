import sqlite3
from datetime import datetime
from pathlib import Path


LATEST_SCHEMA_VERSION = 4


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



def _migration_4_quality_capa_foundation(conn):
    conn.executescript(
        QUALITY_CAPA_SCHEMA_SQL
    )


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

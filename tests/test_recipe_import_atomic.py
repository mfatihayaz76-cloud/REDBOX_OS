import sqlite3
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.recipe_import_engine import (
    CatalogValidationError,
    REQUIRED_HEADERS,
    katalog_ice_aktar,
)


SCHEMA = """
CREATE TABLE personeller (
    id INTEGER PRIMARY KEY,
    ad_soyad TEXT NOT NULL
);

CREATE TABLE hammaddeler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT NOT NULL UNIQUE,
    birim TEXT NOT NULL DEFAULT 'kg',
    aktif INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE urunler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    urun_kodu TEXT NOT NULL UNIQUE COLLATE NOCASE,
    urun_adi TEXT NOT NULL UNIQUE COLLATE NOCASE,
    kategori TEXT,
    barkod TEXT UNIQUE,
    birim TEXT NOT NULL DEFAULT 'KG',
    raf_omru_gun INTEGER,
    saklama_sicakligi TEXT,
    aktif INTEGER NOT NULL DEFAULT 1,
    aciklama TEXT,
    kayit_zamani TEXT NOT NULL
);

CREATE TABLE receteler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT NOT NULL UNIQUE,
    parti_teorik_kg REAL NOT NULL,
    aktif INTEGER NOT NULL DEFAULT 1,
    revizyon_no TEXT,
    gecerlilik_tarihi TEXT,
    revizyon_aciklamasi TEXT,
    olusturan_personel_id INTEGER,
    urun_id INTEGER REFERENCES urunler(id),
    recete_kodu TEXT COLLATE NOCASE,
    proses_suyu_kg REAL NOT NULL DEFAULT 0,
    durum TEXT NOT NULL DEFAULT 'TASLAK',
    onaylayan_personel_id INTEGER,
    onay_zamani TEXT,
    icerik_sha256 TEXT
);

CREATE UNIQUE INDEX ux_receteler_catalog_revision
ON receteler (
    urun_id,
    recete_kodu,
    revizyon_no
);

CREATE UNIQUE INDEX ux_receteler_urun_aktif
ON receteler (urun_id)
WHERE aktif = 1;

CREATE TABLE recete_kalemleri (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recete_id INTEGER NOT NULL
        REFERENCES receteler(id),
    hammadde_id INTEGER NOT NULL
        REFERENCES hammaddeler(id),
    miktar_kg REAL NOT NULL,
    UNIQUE(recete_id, hammadde_id)
);

CREATE TABLE denetim_kayitlari (
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
);
"""


class RecipeImportAtomicTest(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.execute(
            """
            INSERT INTO personeller (
                id,
                ad_soyad
            )
            VALUES (1, 'Fatih Ayaz')
            """
        )
        self.conn.executemany(
            """
            INSERT INTO hammaddeler (
                id,
                ad,
                birim,
                aktif
            )
            VALUES (?, ?, 'kg', 1)
            """,
            (
                (1, "Patates Unu"),
                (2, "Nişasta"),
            ),
        )
        self.conn.commit()

        self.user = {
            "hesap_id": 1,
            "personel_id": 1,
            "kullanici_adi": "fatih",
            "ad_soyad": "Fatih Ayaz",
            "oturum_id": "crc2-test-session",
        }

    def tearDown(self):
        self.conn.close()

    def row(self, **changes):
        row = {
            "_satir": 2,
            "urun_kodu": "CRC2001",
            "urun_adi": "CRC-2 Test Ürünü",
            "kategori": "Test",
            "barkod": "",
            "birim": "KG",
            "raf_omru_gun": "365",
            "saklama_sicakligi": "-18°C",
            "urun_aciklama": "Atomik import testi",
            "recete_kodu": "CRC2001-REC",
            "recete_adi": "CRC-2 TEST ANA REÇETE",
            "revizyon_no": "00",
            "gecerlilik_tarihi": "19.07.2026",
            "durum": "AKTIF",
            "parti_teorik_kg": "2.000",
            "proses_suyu_kg": "1.000",
            "revizyon_aciklamasi": "İlk sürüm",
            "hammadde_adi": "Patates Unu",
            "miktar_kg": "1.000",
        }
        row.update(changes)
        return row

    def counts(self):
        return {
            table: self.conn.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            for table in (
                "urunler",
                "receteler",
                "recete_kalemleri",
                "denetim_kayitlari",
            )
        }

    def test_successful_import_is_atomic_and_audited(self):
        result = katalog_ice_aktar(
            self.conn,
            REQUIRED_HEADERS,
            [self.row()],
            kullanici=self.user,
            kaynak_adi="catalog.xlsx",
        )

        self.assertTrue(result["gecerli"])
        self.assertEqual(
            self.counts(),
            {
                "urunler": 1,
                "receteler": 1,
                "recete_kalemleri": 1,
                "denetim_kayitlari": 1,
            },
        )

        recipe = self.conn.execute(
            """
            SELECT *
            FROM receteler
            """
        ).fetchone()

        self.assertEqual(recipe["durum"], "AKTIF")
        self.assertEqual(recipe["aktif"], 1)
        self.assertEqual(
            recipe["olusturan_personel_id"],
            1,
        )
        self.assertEqual(
            recipe["onaylayan_personel_id"],
            1,
        )
        self.assertIsNotNone(recipe["onay_zamani"])
        self.assertEqual(
            len(recipe["icerik_sha256"]),
            64,
        )

        audit = self.conn.execute(
            """
            SELECT *
            FROM denetim_kayitlari
            """
        ).fetchone()

        self.assertEqual(audit["modul"], "RECETE")
        self.assertEqual(audit["islem"], "OLUSTURMA")
        self.assertEqual(
            audit["kayit_turu"],
            "recete_katalog_importu",
        )
        self.assertEqual(
            audit["kullanici_adi"],
            "fatih",
        )

    def test_61_product_catalog_atomic_import(self):
        rows = []

        for number in range(1, 62):
            rows.append(
                self.row(
                    _satir=number + 1,
                    urun_kodu=f"BULK{number:03d}",
                    urun_adi=(
                        f"Toplu Test Ürünü {number:03d}"
                    ),
                    recete_kodu=(
                        f"BULK{number:03d}-REC"
                    ),
                    recete_adi=(
                        "TOPLU TEST ÜRÜNÜ "
                        f"{number:03d} ANA REÇETE"
                    ),
                )
            )

        result = katalog_ice_aktar(
            self.conn,
            REQUIRED_HEADERS,
            rows,
            kullanici=self.user,
            kaynak_adi="61-product-catalog.xlsx",
        )

        self.assertTrue(result["gecerli"])
        self.assertEqual(
            result["ozet"]["yeni_urun_sayisi"],
            61,
        )
        self.assertEqual(
            result["ozet"]["recete_sayisi"],
            61,
        )
        self.assertEqual(
            result["ozet"]["kalem_sayisi"],
            61,
        )
        self.assertEqual(
            self.counts(),
            {
                "urunler": 61,
                "receteler": 61,
                "recete_kalemleri": 61,
                "denetim_kayitlari": 1,
            },
        )

        active_duplicates = self.conn.execute(
            """
            SELECT urun_id, COUNT(*)
            FROM receteler
            WHERE aktif = 1
            GROUP BY urun_id
            HAVING COUNT(*) > 1
            """
        ).fetchall()

        self.assertEqual(active_duplicates, [])
        self.assertEqual(
            self.conn.execute(
                "PRAGMA foreign_key_check"
            ).fetchall(),
            [],
        )
        self.assertEqual(
            self.conn.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0],
            "ok",
        )

    def test_two_material_recipe_import(self):
        first = self.row(
            parti_teorik_kg="2.000",
            proses_suyu_kg="0.500",
            miktar_kg="1.000",
        )
        second = self.row(
            _satir=3,
            parti_teorik_kg="2.000",
            proses_suyu_kg="0.500",
            hammadde_adi="Nişasta",
            miktar_kg="0.500",
        )

        result = katalog_ice_aktar(
            self.conn,
            REQUIRED_HEADERS,
            [first, second],
            kullanici=self.user,
        )

        self.assertEqual(
            result["ozet"]["kalem_sayisi"],
            2,
        )
        self.assertEqual(
            self.conn.execute(
                """
                SELECT COUNT(*)
                FROM recete_kalemleri
                """
            ).fetchone()[0],
            2,
        )

    def test_invalid_preflight_writes_nothing(self):
        before = self.counts()

        with self.assertRaises(
            CatalogValidationError
        ):
            katalog_ice_aktar(
                self.conn,
                REQUIRED_HEADERS,
                [
                    self.row(
                        parti_teorik_kg="9.000"
                    )
                ],
                kullanici=self.user,
            )

        self.assertEqual(self.counts(), before)
        self.assertFalse(self.conn.in_transaction)

    def test_database_failure_rolls_back_everything(self):
        self.conn.execute("""
            CREATE TRIGGER force_recipe_failure
            BEFORE INSERT ON receteler
            WHEN NEW.recete_kodu = 'CRC2001-REC'
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'forced recipe failure'
                );
            END
        """)
        self.conn.commit()
        before = self.counts()

        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "forced recipe failure",
        ):
            katalog_ice_aktar(
                self.conn,
                REQUIRED_HEADERS,
                [self.row()],
                kullanici=self.user,
            )

        self.assertEqual(self.counts(), before)
        self.assertFalse(self.conn.in_transaction)

    def test_approved_import_requires_personnel_identity(self):
        user = {
            "kullanici_adi": "fatih",
            "ad_soyad": "Fatih Ayaz",
        }

        with self.assertRaisesRegex(
            ValueError,
            "personel kimliği",
        ):
            katalog_ice_aktar(
                self.conn,
                REQUIRED_HEADERS,
                [self.row()],
                kullanici=user,
            )

        self.assertEqual(
            self.counts()["urunler"],
            0,
        )

    def test_user_identity_is_required(self):
        with self.assertRaisesRegex(
            ValueError,
            "kullanıcı kimliği",
        ):
            katalog_ice_aktar(
                self.conn,
                REQUIRED_HEADERS,
                [self.row()],
                kullanici={},
            )

        self.assertEqual(
            self.counts()["urunler"],
            0,
        )

    def test_existing_transaction_is_rejected(self):
        self.conn.execute("BEGIN")

        try:
            with self.assertRaisesRegex(
                RuntimeError,
                "temiz bir bağlantıda",
            ):
                katalog_ice_aktar(
                    self.conn,
                    REQUIRED_HEADERS,
                    [self.row()],
                    kullanici=self.user,
                )
        finally:
            self.conn.rollback()

        self.assertEqual(
            self.counts()["urunler"],
            0,
        )

    def test_content_hash_is_deterministic(self):
        first_row = self.row()
        katalog_ice_aktar(
            self.conn,
            REQUIRED_HEADERS,
            [first_row],
            kullanici=self.user,
        )
        first_hash = self.conn.execute(
            """
            SELECT icerik_sha256
            FROM receteler
            """
        ).fetchone()[0]

        second = sqlite3.connect(":memory:")
        second.row_factory = sqlite3.Row
        second.execute("PRAGMA foreign_keys = ON")
        second.executescript(SCHEMA)
        second.execute(
            """
            INSERT INTO personeller
            VALUES (1, 'Fatih Ayaz')
            """
        )
        second.executemany(
            """
            INSERT INTO hammaddeler (
                id,
                ad,
                birim,
                aktif
            )
            VALUES (?, ?, 'kg', 1)
            """,
            (
                (1, "Patates Unu"),
                (2, "Nişasta"),
            ),
        )
        second.commit()

        try:
            katalog_ice_aktar(
                second,
                REQUIRED_HEADERS,
                [first_row],
                kullanici=self.user,
            )
            second_hash = second.execute(
                """
                SELECT icerik_sha256
                FROM receteler
                """
            ).fetchone()[0]
        finally:
            second.close()

        self.assertEqual(first_hash, second_hash)


if __name__ == "__main__":
    unittest.main(verbosity=2)

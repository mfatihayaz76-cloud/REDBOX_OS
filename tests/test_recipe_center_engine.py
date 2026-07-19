import sqlite3
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from database.recipe_approval_engine import (
    recete_icerik_sha256,
)
from database.recipe_center_engine import (
    recete_katalog_ozeti,
    recete_katalogunu_getir,
    recete_kalemlerini_getir,
)


SCHEMA = """
CREATE TABLE urunler (
    id INTEGER PRIMARY KEY,
    urun_kodu TEXT NOT NULL,
    urun_adi TEXT NOT NULL,
    kategori TEXT,
    barkod TEXT,
    birim TEXT NOT NULL DEFAULT 'KG',
    raf_omru_gun INTEGER,
    saklama_sicakligi TEXT,
    aktif INTEGER NOT NULL DEFAULT 1,
    aciklama TEXT,
    kayit_zamani TEXT NOT NULL
);

CREATE TABLE personeller (
    id INTEGER PRIMARY KEY,
    ad_soyad TEXT NOT NULL
);

CREATE TABLE receteler (
    id INTEGER PRIMARY KEY,
    ad TEXT NOT NULL,
    parti_teorik_kg REAL NOT NULL,
    aktif INTEGER NOT NULL DEFAULT 1,
    revizyon_no TEXT,
    gecerlilik_tarihi TEXT,
    revizyon_aciklamasi TEXT,
    olusturan_personel_id INTEGER,
    urun_id INTEGER,
    recete_kodu TEXT,
    proses_suyu_kg REAL NOT NULL DEFAULT 0,
    durum TEXT NOT NULL DEFAULT 'TASLAK',
    onaylayan_personel_id INTEGER,
    onay_zamani TEXT,
    icerik_sha256 TEXT
);

CREATE TABLE hammaddeler (
    id INTEGER PRIMARY KEY,
    ad TEXT NOT NULL
);

CREATE TABLE recete_kalemleri (
    id INTEGER PRIMARY KEY,
    recete_id INTEGER NOT NULL,
    hammadde_id INTEGER NOT NULL,
    miktar_kg REAL NOT NULL
);

CREATE TABLE uretim_recete (
    id INTEGER PRIMARY KEY,
    uretim_id INTEGER NOT NULL,
    recete_id INTEGER NOT NULL
);

CREATE TABLE dijital_onaylar (
    id INTEGER PRIMARY KEY,
    kaynak_turu TEXT NOT NULL,
    kaynak_id INTEGER NOT NULL,
    onay_turu TEXT NOT NULL,
    karar TEXT NOT NULL,
    kullanici_id INTEGER NOT NULL,
    personel_id INTEGER NOT NULL,
    kullanici_adi TEXT NOT NULL,
    ad_soyad TEXT NOT NULL,
    onay_zamani TEXT NOT NULL,
    aciklama TEXT,
    icerik_sha256 TEXT NOT NULL,
    oturum_id TEXT
);
"""


class RecipeCenterEngineTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

        self.conn.executemany(
            """
            INSERT INTO urunler (
                id,
                urun_kodu,
                urun_adi,
                kategori,
                barkod,
                aktif,
                kayit_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, 'NOW')
            """,
            (
                (
                    1,
                    "LP001",
                    "Long Potato",
                    "HAMUR",
                    "8690001",
                    1,
                ),
                (
                    2,
                    "PZ001",
                    "Pizza Baharatı",
                    "TOZ",
                    "8690002",
                    1,
                ),
                (
                    3,
                    "OLD001",
                    "Pasif Ürün",
                    "ARSIV",
                    "8690003",
                    0,
                ),
            ),
        )

        self.conn.executemany(
            """
            INSERT INTO personeller (
                id,
                ad_soyad
            )
            VALUES (?, ?)
            """,
            (
                (1, "Fatih Ayaz"),
                (2, "Kalite Sorumlusu"),
            ),
        )

        self.conn.executemany(
            """
            INSERT INTO hammaddeler (
                id,
                ad
            )
            VALUES (?, ?)
            """,
            (
                (1, "Patates Unu"),
                (2, "Baharat Karışımı"),
            ),
        )

        self.conn.executemany(
            """
            INSERT INTO receteler (
                id,
                ad,
                parti_teorik_kg,
                aktif,
                revizyon_no,
                gecerlilik_tarihi,
                revizyon_aciklamasi,
                olusturan_personel_id,
                urun_id,
                recete_kodu,
                proses_suyu_kg,
                durum,
                onaylayan_personel_id,
                onay_zamani,
                icerik_sha256
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                (
                    1,
                    "Long Potato Reçetesi",
                    20.0,
                    1,
                    "01",
                    "20.07.2027",
                    "Aktif revizyon",
                    1,
                    1,
                    "LP001-REC",
                    10.0,
                    "AKTIF",
                    2,
                    "19.07.2026 20:00:00",
                    "sha-lp",
                ),
                (
                    2,
                    "Long Potato Reçetesi",
                    19.0,
                    0,
                    "00",
                    "20.07.2026",
                    "Arşiv revizyon",
                    1,
                    1,
                    "LP001-REC",
                    9.0,
                    "ARSIV",
                    None,
                    None,
                    "sha-old",
                ),
                (
                    3,
                    "Pizza Baharatı Reçetesi",
                    5.0,
                    1,
                    "01",
                    "20.07.2027",
                    "Susuz reçete",
                    1,
                    2,
                    "PZ001-REC",
                    0.0,
                    "AKTIF",
                    None,
                    None,
                    "sha-pz",
                ),
                (
                    4,
                    "Pasif Ürün Reçetesi",
                    1.0,
                    1,
                    "01",
                    "20.07.2027",
                    "Pasif ürün",
                    1,
                    3,
                    "OLD001-REC",
                    0.0,
                    "AKTIF",
                    None,
                    None,
                    "sha-old-product",
                ),
            ),
        )

        self.conn.executemany(
            """
            INSERT INTO recete_kalemleri (
                id,
                recete_id,
                hammadde_id,
                miktar_kg
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                (1, 1, 1, 10.0),
                (2, 2, 1, 10.0),
                (3, 3, 2, 5.0),
                (4, 4, 2, 1.0),
            ),
        )

        self.conn.execute(
            """
            INSERT INTO uretim_recete (
                id,
                uretim_id,
                recete_id
            )
            VALUES (1, 100, 1)
            """
        )

        self.conn.execute(
            """
            INSERT INTO dijital_onaylar (
                id,
                kaynak_turu,
                kaynak_id,
                onay_turu,
                karar,
                kullanici_id,
                personel_id,
                kullanici_adi,
                ad_soyad,
                onay_zamani,
                aciklama,
                icerik_sha256,
                oturum_id
            )
            VALUES (
                1,
                'RECETE',
                1,
                'RECETE_ONAYI',
                'ONAYLANDI',
                1,
                2,
                'kalite',
                'Kalite Sorumlusu',
                '19.07.2026 20:00:00',
                'Reçete onaylandı.',
                'sha-lp',
                'session-1'
            )
            """
        )

        current_hash = recete_icerik_sha256(
            self.conn,
            1,
        )

        self.conn.execute(
            """
            UPDATE receteler
            SET icerik_sha256 = ?
            WHERE id = 1
            """,
            (current_hash,),
        )

        self.conn.execute(
            """
            UPDATE dijital_onaylar
            SET icerik_sha256 = ?
            WHERE id = 1
            """,
            (current_hash,),
        )

        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_catalog_summary_and_mass_balance(self):
        rows = recete_katalogunu_getir(
            self.conn
        )
        summary = recete_katalog_ozeti(rows)

        self.assertEqual(summary["kayit_sayisi"], 3)
        self.assertEqual(summary["urun_sayisi"], 2)
        self.assertEqual(summary["aktif_recete_sayisi"], 2)
        self.assertEqual(summary["onayli_recete_sayisi"], 1)
        self.assertEqual(summary["kutle_dengesi_hatasi"], 0)

    def test_status_filter(self):
        rows = recete_katalogunu_getir(
            self.conn,
            durum="ARSIV",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["recete_id"], 2)

    def test_catalog_search_across_identity_fields(self):
        for search_value in (
            "LP001",
            "Long Potato",
            "8690001",
            "aktif revizyon",
        ):
            with self.subTest(search_value=search_value):
                rows = recete_katalogunu_getir(
                    self.conn,
                    arama=search_value,
                )
                self.assertEqual(
                    {row["urun_id"] for row in rows},
                    {1},
                )

    def test_zero_water_recipe_mass_balance(self):
        rows = recete_katalogunu_getir(
            self.conn,
            urun_id=2,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["proses_suyu_kg"], 0.0)
        self.assertTrue(rows[0]["kutle_dengesi_uyumlu"])

    def test_inactive_products_hidden_by_default(self):
        rows = recete_katalogunu_getir(
            self.conn
        )

        self.assertNotIn(
            3,
            {row["urun_id"] for row in rows},
        )

        all_rows = recete_katalogunu_getir(
            self.conn,
            yalniz_aktif_urunler=False,
        )

        self.assertIn(
            3,
            {row["urun_id"] for row in all_rows},
        )

    def test_digital_approval_requires_current_hash(self):
        rows = recete_katalogunu_getir(
            self.conn,
            urun_id=1,
        )

        approved = next(
            row
            for row in rows
            if row["recete_id"] == 1
        )

        self.assertTrue(
            approved["gecerli_dijital_onay"]
        )

        self.conn.execute(
            """
            UPDATE recete_kalemleri
            SET miktar_kg = miktar_kg + 0.250
            WHERE recete_id = 1
              AND id = 1
            """
        )

        rows = recete_katalogunu_getir(
            self.conn,
            urun_id=1,
        )

        changed = next(
            row
            for row in rows
            if row["recete_id"] == 1
        )

        self.assertFalse(
            changed["gecerli_dijital_onay"]
        )

    def test_recipe_items_contract(self):
        rows = recete_kalemlerini_getir(
            self.conn,
            1,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["hammadde"],
            "Patates Unu",
        )

    def test_invalid_filters_are_rejected(self):
        with self.assertRaises(ValueError):
            recete_katalogunu_getir(
                self.conn,
                durum="UNKNOWN",
            )

        with self.assertRaises(ValueError):
            recete_katalogunu_getir(
                self.conn,
                urun_id=0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

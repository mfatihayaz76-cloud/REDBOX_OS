import ast
import sqlite3
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.migrations import (
    _migration_10_commercial_recipe_catalog_contract,
)


BASE_SCHEMA = """
CREATE TABLE personeller (
    id INTEGER PRIMARY KEY,
    ad_soyad TEXT NOT NULL
);

CREATE TABLE urunler (
    id INTEGER PRIMARY KEY,
    urun_kodu TEXT NOT NULL
);

CREATE TABLE receteler (
    id INTEGER PRIMARY KEY,
    ad TEXT NOT NULL,
    parti_teorik_kg REAL NOT NULL,
    revizyon_no TEXT,
    gecerlilik_tarihi TEXT,
    revizyon_aciklamasi TEXT,
    olusturan_personel_id INTEGER,
    aktif INTEGER NOT NULL DEFAULT 0,
    urun_id INTEGER NOT NULL,
    FOREIGN KEY (olusturan_personel_id)
        REFERENCES personeller(id),
    FOREIGN KEY (urun_id)
        REFERENCES urunler(id)
);

CREATE TABLE recete_kalemleri (
    id INTEGER PRIMARY KEY,
    recete_id INTEGER NOT NULL,
    hammadde_id INTEGER NOT NULL,
    miktar_kg REAL NOT NULL,
    FOREIGN KEY (recete_id)
        REFERENCES receteler(id)
);

CREATE TABLE uretim_recete (
    id INTEGER PRIMARY KEY,
    recete_id INTEGER NOT NULL,
    FOREIGN KEY (recete_id)
        REFERENCES receteler(id)
);

CREATE TABLE sistem_ayarlari (
    anahtar TEXT PRIMARY KEY,
    deger TEXT
);
"""


def create_connection(
    theoretical_kg=20.0,
    stocked_kg=10.0,
    legacy_water="10.0",
):
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(BASE_SCHEMA)

    conn.execute(
        """
        INSERT INTO personeller (id, ad_soyad)
        VALUES (1, 'Fatih Ayaz')
        """
    )
    conn.execute(
        """
        INSERT INTO urunler (id, urun_kodu)
        VALUES (1, 'TEST 001')
        """
    )
    conn.execute(
        """
        INSERT INTO receteler (
            id,
            ad,
            parti_teorik_kg,
            revizyon_no,
            gecerlilik_tarihi,
            revizyon_aciklamasi,
            olusturan_personel_id,
            aktif,
            urun_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "Test Reçetesi",
            theoretical_kg,
            "00",
            "19.07.2026",
            "CRC-1 sözleşme testi",
            1,
            1,
            1,
        ),
    )
    conn.execute(
        """
        INSERT INTO recete_kalemleri (
            id,
            recete_id,
            hammadde_id,
            miktar_kg
        )
        VALUES (1, 1, 101, ?)
        """,
        (stocked_kg,),
    )

    if legacy_water is not None:
        conn.execute(
            """
            INSERT INTO sistem_ayarlari (
                anahtar,
                deger
            )
            VALUES (
                'PARTI_PROSES_SUYU_KG',
                ?
            )
            """,
            (legacy_water,),
        )

    return conn


class CommercialRecipeCatalogContractTest(
    unittest.TestCase
):

    def test_required_columns_and_indexes_exist(self):
        conn = create_connection()

        try:
            _migration_10_commercial_recipe_catalog_contract(
                conn
            )

            columns = {
                row[1]
                for row in conn.execute(
                    "PRAGMA table_info(receteler)"
                ).fetchall()
            }
            indexes = {
                row[1]
                for row in conn.execute(
                    "PRAGMA index_list(receteler)"
                ).fetchall()
            }

            self.assertTrue(
                {
                    "recete_kodu",
                    "proses_suyu_kg",
                    "durum",
                    "onaylayan_personel_id",
                    "onay_zamani",
                    "icerik_sha256",
                }.issubset(columns)
            )
            self.assertTrue(
                {
                    "ux_receteler_catalog_revision",
                    "idx_receteler_catalog_status",
                }.issubset(indexes)
            )
        finally:
            conn.close()

    def test_legacy_water_and_catalog_backfill(self):
        conn = create_connection(
            theoretical_kg=20.412,
            stocked_kg=9.712,
            legacy_water="10.700",
        )

        try:
            _migration_10_commercial_recipe_catalog_contract(
                conn
            )

            row = conn.execute(
                """
                SELECT
                    recete_kodu,
                    proses_suyu_kg,
                    durum
                FROM receteler
                WHERE id = 1
                """
            ).fetchone()

            self.assertEqual(row[0], "TEST-001-REC")
            self.assertAlmostEqual(row[1], 10.7)
            self.assertEqual(row[2], "AKTIF")
        finally:
            conn.close()

    def test_zero_water_recipe_is_supported(self):
        conn = create_connection(
            theoretical_kg=20.0,
            stocked_kg=20.0,
            legacy_water=None,
        )

        try:
            _migration_10_commercial_recipe_catalog_contract(
                conn
            )

            water = conn.execute(
                """
                SELECT proses_suyu_kg
                FROM receteler
                WHERE id = 1
                """
            ).fetchone()[0]

            self.assertEqual(water, 0.0)

            stock_movement_tables = {
                row[0]
                for row in conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
                if "su_hareket" in row[0].lower()
            }
            self.assertEqual(stock_movement_tables, set())
        finally:
            conn.close()

    def test_negative_legacy_water_is_rejected(self):
        conn = create_connection(
            theoretical_kg=10.0,
            stocked_kg=10.0,
            legacy_water="-1",
        )

        try:
            with self.assertRaisesRegex(
                RuntimeError,
                "negatif olamaz",
            ):
                _migration_10_commercial_recipe_catalog_contract(
                    conn
                )
        finally:
            conn.close()

    def test_invalid_mass_balance_is_rejected(self):
        conn = create_connection(
            theoretical_kg=20.0,
            stocked_kg=10.0,
            legacy_water="5.0",
        )

        try:
            with self.assertRaisesRegex(
                RuntimeError,
                "uyumsuz kayıtlar",
            ):
                _migration_10_commercial_recipe_catalog_contract(
                    conn
                )
        finally:
            conn.close()

    def test_app_runtime_uses_recipe_based_water(self):
        app_path = PROJECT_ROOT / "app.py"
        source = app_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        lines = source.splitlines()

        target_methods = {
            "uretim_kutle_dengesi_getir",
            "recete_verilerini_getir",
            "recete_revizyon_formu_ac",
            "recete_revizyon_kaydet",
            "recete_revizyon_duzenleme_formu_ac",
            "recete_revizyon_duzenleme_kaydet",
        }

        segments = {}

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name in target_methods
            ):
                segments[node.name] = "\n".join(
                    lines[
                        node.lineno - 1:node.end_lineno
                    ]
                )

        self.assertEqual(
            set(segments),
            target_methods,
        )

        for name, segment in segments.items():
            self.assertIn(
                "proses_suyu_kg",
                segment,
                msg=name,
            )
            self.assertNotIn(
                "PARTI_PROSES_SUYU_KG",
                segment,
                msg=name,
            )

        for name in {
            "recete_revizyon_formu_ac",
            "recete_revizyon_kaydet",
            "recete_revizyon_duzenleme_formu_ac",
            "recete_revizyon_duzenleme_kaydet",
        }:
            self.assertIn(
                "proses_suyu_entry",
                segments[name],
                msg=name,
            )

        for name in {
            "recete_revizyon_kaydet",
            "recete_revizyon_duzenleme_kaydet",
        }:
            self.assertIn(
                "Proses suyu negatif olamaz.",
                segments[name],
                msg=name,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

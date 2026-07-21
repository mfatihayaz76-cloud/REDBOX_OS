import sqlite3
import unittest

from database.migrations import (
    LATEST_SCHEMA_VERSION,
    _migration_15_prerequisite_programs,
)


EXPECTED_TABLES = {
    "prp_programlari",
    "prp_kayitlari",
    "prp_aksiyonlari",
    "prp_alerjen_matrisi",
    "prp_ekipmanlari",
    "prp_egitim_katilimlari",
    "prp_risk_degerlendirmeleri",
}

EXPECTED_INDEXES = {
    "idx_prp_program_tur_durum",
    "idx_prp_kayit_program_tarih",
    "idx_prp_aksiyon_kayit_durum",
    "idx_prp_alerjen_urun",
    "idx_prp_ekipman_tur_durum",
    "idx_prp_egitim_personel",
    "idx_prp_risk_tur_durum",
}

PROGRAM_TYPES = {
    "ALERJEN",
    "KALIBRASYON",
    "BAKIM_ARIZA",
    "ZARARLI_MUCADELESI",
    "EGITIM_YETKINLIK",
    "TACCP",
    "VACCP",
}


class PrerequisiteProgramsMigrationTest(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript("""
            CREATE TABLE personeller (
                id INTEGER PRIMARY KEY
            );

            CREATE TABLE urunler (
                id INTEGER PRIMARY KEY
            );
        """)
        self.conn.execute("PRAGMA foreign_keys = ON")

    def tearDown(self):
        self.conn.close()

    def test_latest_schema_is_15(self):
        self.assertEqual(LATEST_SCHEMA_VERSION, 15)

    def test_migration_creates_prp_contract(self):
        _migration_15_prerequisite_programs(self.conn)

        tables = {
            row[0]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        indexes = {
            row[0]
            for row in self.conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='index' AND sql IS NOT NULL
                """
            )
        }

        self.assertTrue(EXPECTED_TABLES <= tables)
        self.assertTrue(EXPECTED_INDEXES <= indexes)

    def test_all_roadmap_program_types_are_accepted(self):
        _migration_15_prerequisite_programs(self.conn)

        for program_type in sorted(PROGRAM_TYPES):
            self.conn.execute(
                """
                INSERT INTO prp_programlari (
                    program_kodu,
                    program_turu,
                    baslik,
                    durum
                )
                VALUES (?, ?, ?, 'TASLAK')
                """,
                (
                    f"PRP-{program_type}",
                    program_type,
                    program_type,
                ),
            )

        stored = {
            row[0]
            for row in self.conn.execute(
                "SELECT program_turu FROM prp_programlari"
            )
        }
        self.assertEqual(stored, PROGRAM_TYPES)

    def test_program_type_and_status_constraints(self):
        _migration_15_prerequisite_programs(self.conn)

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO prp_programlari (
                    program_kodu,
                    program_turu,
                    baslik,
                    durum
                )
                VALUES ('PRP-X', 'GECERSIZ', 'Geçersiz', 'TASLAK')
                """
            )

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO prp_programlari (
                    program_kodu,
                    program_turu,
                    baslik,
                    durum
                )
                VALUES ('PRP-Y', 'ALERJEN', 'Alerjen', 'GECERSIZ')
                """
            )

    def test_migration_is_idempotent(self):
        _migration_15_prerequisite_programs(self.conn)
        _migration_15_prerequisite_programs(self.conn)

        table_count = self.conn.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='table' AND name LIKE 'prp_%'
            """
        ).fetchone()[0]
        self.assertEqual(table_count, len(EXPECTED_TABLES))


if __name__ == "__main__":
    unittest.main()

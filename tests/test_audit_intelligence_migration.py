import sqlite3
import unittest

from database.migrations import (
    LATEST_SCHEMA_VERSION,
    _migration_16_audit_intelligence,
)


EXPECTED_TABLES = {
    "gfs_ic_denetimleri",
    "gfs_musteri_sikayetleri",
    "gfs_laboratuvar_numuneleri",
    "gfs_urun_durum_kayitlari",
    "gfs_yonetim_gozden_gecirmeleri",
    "gfs_tedarikci_riskleri",
    "gfs_mock_recall_testleri",
}

EXPECTED_INDEXES = {
    "idx_gfs_denetim_tarih_durum",
    "idx_gfs_sikayet_tarih_durum",
    "idx_gfs_numune_tarih_durum",
    "idx_gfs_urun_durum_lot",
    "idx_gfs_ygd_tarih_durum",
    "idx_gfs_tedarikci_risk",
    "idx_gfs_mock_recall_tarih",
}


class AuditIntelligenceMigrationTest(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript("""
            CREATE TABLE personeller (
                id INTEGER PRIMARY KEY
            );
            CREATE TABLE musteriler (
                id INTEGER PRIMARY KEY
            );
            CREATE TABLE tedarikciler (
                id INTEGER PRIMARY KEY
            );
            CREATE TABLE urunler (
                id INTEGER PRIMARY KEY
            );
        """)
        self.conn.execute("PRAGMA foreign_keys = ON")

    def tearDown(self):
        self.conn.close()

    def test_latest_schema_is_16(self):
        self.assertGreaterEqual(LATEST_SCHEMA_VERSION, 16)

    def test_migration_creates_audit_intelligence_contract(self):
        _migration_16_audit_intelligence(self.conn)

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

    def test_product_disposition_constraint(self):
        _migration_16_audit_intelligence(self.conn)

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO gfs_urun_durum_kayitlari (
                    lot_kodu,
                    durum,
                    karar_tarihi
                )
                VALUES ('LOT-X', 'GECERSIZ', '21.07.2026')
                """
            )

    def test_supplier_risk_score_constraint(self):
        _migration_16_audit_intelligence(self.conn)

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """
                INSERT INTO gfs_tedarikci_riskleri (
                    tedarikci_id,
                    degerlendirme_tarihi,
                    kalite_puani,
                    teslimat_puani,
                    gida_guvenligi_puani,
                    toplam_risk_puani,
                    risk_seviyesi
                )
                VALUES (
                    1, '21.07.2026',
                    101, 50, 50, 50, 'ORTA'
                )
                """
            )

    def test_migration_is_idempotent(self):
        _migration_16_audit_intelligence(self.conn)
        _migration_16_audit_intelligence(self.conn)

        count = self.conn.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='table' AND name LIKE 'gfs_%'
            """
        ).fetchone()[0]
        self.assertEqual(count, len(EXPECTED_TABLES))


if __name__ == "__main__":
    unittest.main()

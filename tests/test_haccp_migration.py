import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.migrations import (
    LATEST_SCHEMA_VERSION,
    _migration_14_haccp_engine,
    run_migrations,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"

EXPECTED_TABLES = {
    "haccp_planlari",
    "haccp_proses_adimlari",
    "haccp_akis_dogrulamalari",
    "haccp_tehlikeleri",
    "haccp_tehlike_degerlendirmeleri",
    "haccp_kontrol_noktalari",
    "haccp_kritik_limitleri",
    "haccp_izleme_planlari",
    "haccp_sapmalari",
    "haccp_dogrulamalari",
}

EXPECTED_INDEXES = {
    "idx_haccp_plan_urun_durum",
    "idx_haccp_proses_plan_sira",
    "idx_haccp_tehlike_adim_tur",
    "idx_haccp_degerlendirme_risk",
    "idx_haccp_kontrol_sinif",
    "idx_haccp_izleme_kontrol",
    "idx_haccp_sapma_durum",
    "idx_haccp_dogrulama_plan_tarih",
}


class HaccpMigrationTest(unittest.TestCase):

    def setUp(self):
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

    def tearDown(self):
        self.assertEqual(
            hashlib.sha256(
                LIVE_DB.read_bytes()
            ).hexdigest(),
            self.live_sha,
        )

    def _sandbox(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        database = Path(temporary.name) / "haccp.db"
        shutil.copy2(LIVE_DB, database)
        return database

    def test_latest_schema_includes_haccp_14(self):
        self.assertGreaterEqual(LATEST_SCHEMA_VERSION, 14)

    def test_migration_14_creates_haccp_contract(self):
        database = self._sandbox()
        run_migrations(database)

        connection = sqlite3.connect(database)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
            }
            indexes = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'index'
                    """
                ).fetchall()
            }
            migration = connection.execute(
                """
                SELECT version, name
                FROM schema_migrations
                WHERE version = 14
                """
            ).fetchone()
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
        finally:
            connection.close()

        self.assertTrue(EXPECTED_TABLES.issubset(tables))
        self.assertTrue(EXPECTED_INDEXES.issubset(indexes))
        self.assertEqual(
            migration,
            (14, "haccp_engine"),
        )
        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])

    def test_hazard_and_control_classification_constraints(self):
        database = self._sandbox()
        run_migrations(database)
        connection = sqlite3.connect(database)

        try:
            connection.execute(
                """
                INSERT INTO haccp_tehlikeleri (
                    tehlike_kodu,
                    ad,
                    tehlike_turu,
                    aciklama,
                    aktif,
                    kayit_zamani,
                    guncelleme_zamani
                )
                VALUES (
                    'BIO-001',
                    'Patojen mikroorganizma',
                    'BIYOLOJIK',
                    'Biyolojik tehlike',
                    1,
                    '2026-07-21T20:00:00+03:00',
                    '2026-07-21T20:00:00+03:00'
                )
                """
            )

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO haccp_tehlikeleri (
                        tehlike_kodu,
                        ad,
                        tehlike_turu,
                        aciklama,
                        aktif,
                        kayit_zamani,
                        guncelleme_zamani
                    )
                    VALUES (
                        'BAD-001',
                        'Geçersiz',
                        'GECERSIZ',
                        'Geçersiz sınıf',
                        1,
                        '2026-07-21T20:00:00+03:00',
                        '2026-07-21T20:00:00+03:00'
                    )
                    """
                )
        finally:
            connection.close()

    def test_migration_14_is_idempotent(self):
        database = self._sandbox()
        run_migrations(database)
        first_sha = hashlib.sha256(
            database.read_bytes()
        ).hexdigest()

        run_migrations(database)

        connection = sqlite3.connect(database)
        try:
            count = connection.execute(
                """
                SELECT COUNT(*)
                FROM schema_migrations
                WHERE version = 14
                """
            ).fetchone()[0]
            version = connection.execute(
                "PRAGMA user_version"
            ).fetchone()[0]
        finally:
            connection.close()

        self.assertEqual(count, 1)
        self.assertEqual(version, LATEST_SCHEMA_VERSION)
        self.assertTrue(first_sha)

    def test_direct_migration_supports_minimal_prerequisites(self):
        connection = sqlite3.connect(":memory:")
        try:
            connection.executescript(
                """
                CREATE TABLE urunler (
                    id INTEGER PRIMARY KEY
                );
                CREATE TABLE personeller (
                    id INTEGER PRIMARY KEY
                );
                CREATE TABLE kalite_uygunsuzluklari (
                    id INTEGER PRIMARY KEY
                );
                """
            )
            _migration_14_haccp_engine(connection)

            tables = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
            }
        finally:
            connection.close()

        self.assertTrue(EXPECTED_TABLES.issubset(tables))


if __name__ == "__main__":
    unittest.main()

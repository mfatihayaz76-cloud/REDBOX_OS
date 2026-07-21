import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.migrations import (
    LATEST_SCHEMA_VERSION,
    run_migrations,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"


class BackupRecoveryMigrationTest(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = (
            Path(self.temp_dir.name)
            / "backup_recovery_migration.db"
        )
        shutil.copy2(LIVE_DB, self.db_path)
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

    def tearDown(self):
        self.temp_dir.cleanup()

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def test_migration_13_creates_backup_contract(self):
        run_migrations(self.db_path)
        conn = self.connect()

        try:
            version = conn.execute(
                "PRAGMA user_version"
            ).fetchone()[0]
            migration = conn.execute(
                """
                SELECT name
                FROM schema_migrations
                WHERE version = 13
                """
            ).fetchone()
            tables = {
                row[0]
                for row in conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
            }
            policy = conn.execute(
                """
                SELECT aktif, siklik_saat, saklama_adedi
                FROM yedekleme_politikasi
                WHERE id = 1
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertGreaterEqual(LATEST_SCHEMA_VERSION, 13)
        self.assertEqual(version, LATEST_SCHEMA_VERSION)
        self.assertEqual(
            migration,
            ("backup_recovery_foundation",),
        )
        self.assertTrue(
            {
                "yedekleme_politikasi",
                "yedekleme_kayitlari",
                "geri_yukleme_kayitlari",
            }.issubset(tables)
        )
        self.assertEqual(policy, (1, 24, 14))

    def test_backup_policy_constraints(self):
        run_migrations(self.db_path)
        conn = self.connect()

        try:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    UPDATE yedekleme_politikasi
                    SET siklik_saat = 0
                    WHERE id = 1
                    """
                )

            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    UPDATE yedekleme_politikasi
                    SET saklama_adedi = 101
                    WHERE id = 1
                    """
                )
        finally:
            conn.close()

    def test_migration_13_is_idempotent(self):
        run_migrations(self.db_path)
        run_migrations(self.db_path)
        conn = self.connect()

        try:
            migration_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM schema_migrations
                WHERE version = 13
                """
            ).fetchone()[0]
            policy_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM yedekleme_politikasi
                WHERE id = 1
                """
            ).fetchone()[0]
            integrity = conn.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
            foreign_keys = conn.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
        finally:
            conn.close()

        self.assertEqual(migration_count, 1)
        self.assertEqual(policy_count, 1)
        self.assertEqual(integrity, "ok")
        self.assertEqual(foreign_keys, [])

    def test_live_database_is_not_modified(self):
        run_migrations(self.db_path)

        live_after = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

        self.assertEqual(self.live_sha, live_after)


if __name__ == "__main__":
    unittest.main()

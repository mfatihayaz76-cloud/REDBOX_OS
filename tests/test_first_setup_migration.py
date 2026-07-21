import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from database.migrations import (
    LATEST_SCHEMA_VERSION,
    run_migrations,
)


class FirstSetupMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.live_db = cls.root / "database" / "redbox_os.db"
        cls.live_sha = hashlib.sha256(
            cls.live_db.read_bytes()
        ).hexdigest()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sandbox_db = (
            Path(self.temp_dir.name)
            / "redbox_os_com1_migration.db"
        )
        shutil.copy2(self.live_db, self.sandbox_db)

    def tearDown(self):
        self.temp_dir.cleanup()
        self.assertEqual(
            hashlib.sha256(
                self.live_db.read_bytes()
            ).hexdigest(),
            self.live_sha,
        )

    def connect(self):
        conn = sqlite3.connect(self.sandbox_db)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def test_migration_11_creates_company_setup_contract(self):
        run_migrations(self.sandbox_db)

        with closing(self.connect()) as conn:
            tables = {
                row["name"]
                for row in conn.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                """).fetchall()
            }

            self.assertTrue({
                "firma_profili",
                "tesis_profilleri",
                "ilk_kurulum_durumu",
            }.issubset(tables))

            self.assertEqual(
                conn.execute(
                    "PRAGMA user_version"
                ).fetchone()[0],
                LATEST_SCHEMA_VERSION,
            )

            migration = conn.execute("""
                SELECT name
                FROM schema_migrations
                WHERE version = 11
            """).fetchone()

            self.assertEqual(
                migration["name"],
                "company_first_setup_foundation",
            )
            self.assertEqual(
                conn.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0],
                "ok",
            )
            self.assertEqual(
                conn.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall(),
                [],
            )

    def test_migration_11_is_idempotent(self):
        run_migrations(self.sandbox_db)
        run_migrations(self.sandbox_db)

        with closing(self.connect()) as conn:
            count = conn.execute("""
                SELECT COUNT(*)
                FROM schema_migrations
                WHERE version = 11
            """).fetchone()[0]

            self.assertEqual(count, 1)

    def test_completed_setup_requires_full_identity(self):
        run_migrations(self.sandbox_db)

        with closing(self.connect()) as conn:
            with self.assertRaises(
                sqlite3.IntegrityError
            ):
                conn.execute("""
                    INSERT INTO ilk_kurulum_durumu (
                        id,
                        kullanim_modu,
                        tamamlandi,
                        baslama_zamani,
                        tamamlanma_zamani
                    )
                    VALUES (
                        1,
                        'GERCEK',
                        1,
                        '20.07.2026 15:00:00',
                        '20.07.2026 15:01:00'
                    )
                """)

    def test_only_one_active_primary_facility_is_allowed(self):
        run_migrations(self.sandbox_db)

        with closing(self.connect()) as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("DELETE FROM ilk_kurulum_durumu")
            conn.execute("DELETE FROM tesis_profilleri")
            conn.execute("DELETE FROM firma_profili")
            conn.commit()
            conn.execute("PRAGMA foreign_keys = ON")

            conn.execute("""
                INSERT INTO firma_profili (
                    id,
                    ticari_unvan,
                    kisa_ad,
                    kayit_zamani
                )
                VALUES (
                    1,
                    'REDBOX GIDA',
                    'REDBOX',
                    '20.07.2026 15:00:00'
                )
            """)

            conn.execute("""
                INSERT INTO tesis_profilleri (
                    firma_id,
                    tesis_kodu,
                    tesis_adi,
                    ana_tesis,
                    kayit_zamani
                )
                VALUES (
                    1,
                    'TESIS-01',
                    'Ana Üretim Tesisi',
                    1,
                    '20.07.2026 15:00:00'
                )
            """)

            with self.assertRaises(
                sqlite3.IntegrityError
            ):
                conn.execute("""
                    INSERT INTO tesis_profilleri (
                        firma_id,
                        tesis_kodu,
                        tesis_adi,
                        ana_tesis,
                        kayit_zamani
                    )
                    VALUES (
                        1,
                        'TESIS-02',
                        'İkinci Ana Tesis',
                        1,
                        '20.07.2026 15:00:00'
                    )
                """)


if __name__ == "__main__":
    unittest.main()

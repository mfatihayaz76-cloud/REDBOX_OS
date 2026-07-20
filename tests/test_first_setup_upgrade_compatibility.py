import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from database.first_setup_engine import (
    ilk_kurulum_gerekli_mi,
    uygulama_kimligini_getir,
)
from database.migrations import (
    LATEST_SCHEMA_VERSION,
    run_migrations,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"


class FirstSetupUpgradeCompatibilityTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sandbox_db = (
            Path(self.temp_dir.name)
            / "upgrade_compatibility.db"
        )
        shutil.copy2(LIVE_DB, self.sandbox_db)

    def tearDown(self):
        self.temp_dir.cleanup()
        self.assertEqual(
            hashlib.sha256(
                LIVE_DB.read_bytes()
            ).hexdigest(),
            self.live_sha,
        )

    def connect(self):
        conn = sqlite3.connect(self.sandbox_db)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def test_existing_install_does_not_open_wizard(self):
        run_migrations(self.sandbox_db)

        with closing(self.connect()) as conn:
            active_accounts = conn.execute("""
                SELECT COUNT(*)
                FROM kullanici_hesaplari
                WHERE aktif = 1
            """).fetchone()[0]

            setup_rows = conn.execute("""
                SELECT COUNT(*)
                FROM ilk_kurulum_durumu
            """).fetchone()[0]

            schema_version = conn.execute(
                "PRAGMA user_version"
            ).fetchone()[0]

            self.assertGreater(active_accounts, 0)
            self.assertEqual(setup_rows, 0)
            self.assertEqual(
                schema_version,
                LATEST_SCHEMA_VERSION,
            )
            self.assertFalse(
                ilk_kurulum_gerekli_mi(conn)
            )

            identity = uygulama_kimligini_getir(conn)
            self.assertEqual(
                identity["firma_kisa_ad"],
                "REDBOX GIDA",
            )
            self.assertEqual(
                identity["kullanim_modu"],
                "GERCEK",
            )
            self.assertTrue(identity["legacy_kimlik"])

    def test_empty_install_requires_wizard(self):
        run_migrations(self.sandbox_db)

        with closing(self.connect()) as conn:
            conn.execute(
                "DELETE FROM kullanici_hesaplari"
            )
            conn.execute(
                "DELETE FROM ilk_kurulum_durumu"
            )
            conn.execute(
                "DELETE FROM tesis_profilleri"
            )
            conn.execute(
                "DELETE FROM firma_profili"
            )
            conn.commit()

            self.assertTrue(
                ilk_kurulum_gerekli_mi(conn)
            )

    def test_sandbox_integrity_after_migration(self):
        run_migrations(self.sandbox_db)

        with closing(self.connect()) as conn:
            integrity = conn.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
            violations = conn.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            self.assertEqual(integrity, "ok")
            self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

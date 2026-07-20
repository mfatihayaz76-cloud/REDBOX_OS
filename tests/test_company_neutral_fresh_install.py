import hashlib
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database.db as database_module
from database.first_setup_engine import (
    ilk_kurulum_gerekli_mi,
)
from database.migrations import LATEST_SCHEMA_VERSION


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"


class CompanyNeutralFreshInstallTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sandbox_db = (
            Path(self.temp_dir.name)
            / "company_neutral_fresh.db"
        )

        with patch.object(
            database_module,
            "DB_PATH",
            self.sandbox_db,
        ):
            database_module.init_database()

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

    def test_schema_is_current_and_database_is_safe(self):
        with closing(self.connect()) as conn:
            self.assertEqual(
                conn.execute(
                    "PRAGMA user_version"
                ).fetchone()[0],
                LATEST_SCHEMA_VERSION,
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

    def test_no_company_specific_business_seed_exists(self):
        with closing(self.connect()) as conn:
            counts = {
                table: conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                for table in (
                    "sistem_ayarlari",
                    "urunler",
                    "hammaddeler",
                    "receteler",
                    "recete_kalemleri",
                    "personeller",
                    "personel_yetkileri",
                    "kullanici_hesaplari",
                    "firma_profili",
                    "tesis_profilleri",
                    "ilk_kurulum_durumu",
                )
            }

            self.assertEqual(
                counts,
                {table: 0 for table in counts},
            )

    def test_neutral_fresh_install_requires_wizard(self):
        with closing(self.connect()) as conn:
            self.assertTrue(
                ilk_kurulum_gerekli_mi(conn)
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

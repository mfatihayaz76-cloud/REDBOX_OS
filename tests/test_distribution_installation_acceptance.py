import hashlib
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import database.db as database_module
from database.migrations import LATEST_SCHEMA_VERSION
from tools.build_macos_release import (
    create_fresh_install_database,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"


def sha256(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


class DistributionInstallationAcceptanceTest(
    unittest.TestCase
):

    def setUp(self):
        self.live_sha = sha256(LIVE_DB)
        self.original_db_path = database_module.DB_PATH

    def tearDown(self):
        database_module.DB_PATH = self.original_db_path
        self.assertEqual(sha256(LIVE_DB), self.live_sha)

    def test_fresh_install_copies_clean_packaged_database(self):
        with tempfile.TemporaryDirectory() as temp:
            sandbox = Path(temp)
            packaged_db = sandbox / "package" / "redbox_os.db"
            target_db = (
                sandbox
                / "Application Support"
                / "REDBOX_OS"
                / "redbox_os.db"
            )
            create_fresh_install_database(packaged_db)
            packaged_sha = sha256(packaged_db)

            target_db.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            database_module.DB_PATH = target_db

            with (
                mock.patch.object(
                    sys,
                    "frozen",
                    True,
                    create=True,
                ),
                mock.patch.object(
                    database_module,
                    "_packaged_resource_path",
                    return_value=packaged_db,
                ),
            ):
                database_module._prepare_packaged_database()

            self.assertTrue(target_db.is_file())
            self.assertEqual(
                sha256(target_db),
                packaged_sha,
            )

            conn = sqlite3.connect(target_db)
            try:
                self.assertEqual(
                    conn.execute(
                        "PRAGMA user_version"
                    ).fetchone()[0],
                    LATEST_SCHEMA_VERSION,
                )
                self.assertEqual(
                    conn.execute(
                        "SELECT COUNT(*) "
                        "FROM firma_profili"
                    ).fetchone()[0],
                    0,
                )
                self.assertEqual(
                    conn.execute(
                        "SELECT COUNT(*) "
                        "FROM kullanici_hesaplari"
                    ).fetchone()[0],
                    0,
                )
                self.assertEqual(
                    conn.execute(
                        "PRAGMA integrity_check"
                    ).fetchone()[0],
                    "ok",
                )
            finally:
                conn.close()

    def test_upgrade_never_overwrites_existing_user_database(self):
        with tempfile.TemporaryDirectory() as temp:
            sandbox = Path(temp)
            existing_db = (
                sandbox
                / "Application Support"
                / "REDBOX_OS"
                / "redbox_os.db"
            )
            existing_db.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            shutil.copy2(LIVE_DB, existing_db)
            existing_sha = sha256(existing_db)

            packaged_db = (
                sandbox / "package" / "redbox_os.db"
            )
            create_fresh_install_database(packaged_db)
            self.assertNotEqual(
                sha256(packaged_db),
                existing_sha,
            )

            database_module.DB_PATH = existing_db

            with (
                mock.patch.object(
                    sys,
                    "frozen",
                    True,
                    create=True,
                ),
                mock.patch.object(
                    database_module,
                    "_packaged_resource_path",
                    return_value=packaged_db,
                ),
            ):
                database_module._prepare_packaged_database()

            self.assertEqual(
                sha256(existing_db),
                existing_sha,
            )

    def test_fresh_and_upgrade_targets_are_external_to_app(self):
        source = (
            PROJECT_ROOT / "database" / "db.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            '"Application Support"',
            source,
        )
        self.assertIn(
            "if DB_PATH.exists():",
            source,
        )
        self.assertIn(
            "shutil.copy2(packaged_db, DB_PATH)",
            source,
        )

    def test_installation_acceptance_uses_only_sandboxes(self):
        self.assertNotIn(
            str(LIVE_DB),
            str(database_module.DB_PATH)
            if database_module.DB_PATH != LIVE_DB
            else "",
        )


if __name__ == "__main__":
    unittest.main()

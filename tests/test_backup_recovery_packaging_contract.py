import hashlib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"
SPEC_PATH = PROJECT_ROOT / "REDBOX_OS.spec"


class BackupRecoveryPackagingContractTest(unittest.TestCase):

    def setUp(self):
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()
        self.source = SPEC_PATH.read_text(
            encoding="utf-8"
        )

    def test_backup_engine_is_packaged(self):
        self.assertIn(
            '"database.backup_recovery_engine"',
            self.source,
        )

    def test_backup_window_is_packaged(self):
        self.assertIn(
            '"ui.backup_recovery_window"',
            self.source,
        )

    def test_runtime_database_seed_is_preserved(self):
        self.assertIn(
            '"database/redbox_os.db"',
            self.source,
        )

    def test_no_backup_output_is_bundled(self):
        self.assertNotIn(
            '"backups"',
            self.source,
        )
        self.assertNotIn(
            '"restore_request.json"',
            self.source,
        )
        self.assertNotIn(
            '"restore_pending.db"',
            self.source,
        )

    def test_packaging_contract_does_not_modify_live_database(self):
        live_after = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

        self.assertEqual(self.live_sha, live_after)


if __name__ == "__main__":
    unittest.main()

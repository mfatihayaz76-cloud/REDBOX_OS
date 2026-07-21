import ast
import hashlib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"
APP_PATH = PROJECT_ROOT / "app.py"
DB_PATH_SOURCE = PROJECT_ROOT / "database" / "db.py"


class BackupStartupIntegrationTest(unittest.TestCase):

    def setUp(self):
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()
        self.app_source = APP_PATH.read_text(
            encoding="utf-8"
        )
        self.db_source = DB_PATH_SOURCE.read_text(
            encoding="utf-8"
        )
        self.app_tree = ast.parse(self.app_source)

    def test_dynamic_backup_directories_exist(self):
        self.assertIn("BACKUP_DIR", self.db_source)
        self.assertIn("RECOVERY_DIR", self.db_source)
        self.assertIn(
            'getattr(sys, "frozen", False)',
            self.db_source,
        )
        self.assertIn(
            'RECOVERY_DIR = BACKUP_DIR / ".recovery"',
            self.db_source,
        )

    def test_startup_uses_backup_recovery_engine(self):
        self.assertIn(
            "bekleyen_geri_yuklemeyi_uygula",
            self.app_source,
        )
        self.assertIn(
            "otomatik_yedeklemeyi_calistir",
            self.app_source,
        )
        self.assertIn(
            "saklama_politikasini_uygula",
            self.app_source,
        )

    def test_restore_runs_before_database_initialization(self):
        restore_index = self.app_source.index(
            "restore_result = "
            "bekleyen_geri_yuklemeyi_uygula"
        )
        init_index = self.app_source.index(
            "    init_database()",
            restore_index,
        )
        automatic_index = self.app_source.index(
            "otomatik_yedeklemeyi_calistir",
            init_index,
        )

        self.assertLess(restore_index, init_index)
        self.assertLess(init_index, automatic_index)

    def test_entrypoint_uses_controlled_startup(self):
        expected_startup = (
            'if __name__ == "__main__":\n'
            "    _runtime_startup()\n"
            "    _backup_recovery_startup()"
        )
        self.assertIn(
            expected_startup,
            self.app_source,
        )
        self.assertLess(
            self.app_source.index(
                "    _runtime_startup()"
            ),
            self.app_source.index(
                "    _backup_recovery_startup()",
                self.app_source.index(
                    'if __name__ == "__main__":'
                ),
            ),
        )
        self.assertNotIn(
            'if __name__ == "__main__":\n'
            "    init_database()",
            self.app_source,
        )

    def test_startup_closes_maintenance_connection(self):
        functions = {
            node.name: node
            for node in ast.walk(self.app_tree)
            if isinstance(node, ast.FunctionDef)
        }
        startup = functions["_backup_recovery_startup"]
        segment = ast.get_source_segment(
            self.app_source,
            startup,
        )

        self.assertIn(
            "finally:",
            segment,
        )
        self.assertIn(
            "connection.close()",
            segment,
        )

    def test_source_contract_does_not_modify_live_database(self):
        live_after = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

        self.assertEqual(self.live_sha, live_after)


if __name__ == "__main__":
    unittest.main()

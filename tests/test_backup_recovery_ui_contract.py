import ast
import hashlib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"
WINDOW_PATH = (
    PROJECT_ROOT / "ui" / "backup_recovery_window.py"
)
SYSTEM_PATH = PROJECT_ROOT / "ui" / "system.py"


class BackupRecoveryUIContractTest(unittest.TestCase):

    def setUp(self):
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()
        self.window_source = WINDOW_PATH.read_text(
            encoding="utf-8"
        )
        self.system_source = SYSTEM_PATH.read_text(
            encoding="utf-8"
        )
        self.window_tree = ast.parse(
            self.window_source
        )

    def test_professional_backup_center_exists(self):
        classes = {
            node.name
            for node in ast.walk(self.window_tree)
            if isinstance(node, ast.ClassDef)
        }
        self.assertIn(
            "BackupRecoveryWindow",
            classes,
        )

    def test_ui_uses_dynamic_database_paths(self):
        for name in (
            "DB_PATH",
            "BACKUP_DIR",
            "RECOVERY_DIR",
        ):
            self.assertIn(name, self.window_source)

        self.assertNotIn(
            'Path("database/redbox_os.db")',
            self.window_source,
        )

    def test_ui_uses_only_backup_engine_for_writes(self):
        required = (
            "manuel_yedek_olustur",
            "geri_yuklemeyi_hazirla",
            "yedekleme_politikasini_guncelle",
        )

        for name in required:
            self.assertIn(name, self.window_source)

        forbidden = (
            "INSERT INTO",
            "UPDATE yedekleme_",
            "DELETE FROM",
            "os.replace(",
            ".backup(",
            "shutil.copy",
        )

        for value in forbidden:
            self.assertNotIn(value, self.window_source)

    def test_destructive_actions_require_confirmation(self):
        self.assertGreaterEqual(
            self.window_source.count(
                "messagebox.askyesno("
            ),
            3,
        )
        self.assertIn(
            "if not confirmation:",
            self.window_source,
        )

    def test_restore_is_staged_for_restart(self):
        self.assertIn(
            "geri_yuklemeyi_hazirla(",
            self.window_source,
        )
        self.assertIn(
            "Uygulamayı kapatıp yeniden açın",
            self.window_source,
        )
        self.assertNotIn(
            "bekleyen_geri_yuklemeyi_uygula",
            self.window_source,
        )

    def test_system_page_opens_backup_center(self):
        self.assertIn(
            "BackupRecoveryWindow",
            self.system_source,
        )
        self.assertIn(
            "_open_backup_recovery_center",
            self.system_source,
        )
        self.assertNotIn(
            "source_conn.backup(target_conn)",
            self.system_source,
        )
        self.assertNotIn(
            "os.replace(\n"
            "                temporary",
            self.system_source,
        )

    def test_source_contract_does_not_modify_live_database(self):
        live_after = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

        self.assertEqual(self.live_sha, live_after)


if __name__ == "__main__":
    unittest.main()

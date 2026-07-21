import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from application_metadata import APP_BUILD, APP_VERSION
from database.migrations import LATEST_SCHEMA_VERSION

from tools.run_commercial_acceptance import (
    ACCEPTANCE_CRITERIA,
    PERFORMANCE_LIMITS,
    acceptance_test_modules,
    database_performance_probe,
    run_commercial_acceptance,
    validate_release_artifacts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"
DMG_PATH = (
    PROJECT_ROOT
    / "release"
    / "macos"
    / f"REDBOX_OS-{APP_VERSION}-{APP_BUILD}.dmg"
)
MANIFEST_PATH = (
    PROJECT_ROOT
    / "release"
    / "macos"
    / (
        f"REDBOX_OS-{APP_VERSION}-{APP_BUILD}"
        "-manifest.json"
    )
)


class CommercialFinalAcceptanceTest(unittest.TestCase):

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

    def test_all_roadmap_acceptance_criteria_are_mapped(self):
        self.assertEqual(
            set(ACCEPTANCE_CRITERIA),
            {
                "clean_install",
                "first_user",
                "catalog_60_plus",
                "full_business_cycle",
                "traceability_recall",
                "permissions",
                "audit",
                "backup_restore",
                "pdf",
                "performance",
            },
        )

        mapping = acceptance_test_modules()
        self.assertEqual(
            set(mapping),
            set(ACCEPTANCE_CRITERIA),
        )
        for criterion, modules in mapping.items():
            self.assertTrue(
                modules,
                msg=f"Eşlenmemiş kriter: {criterion}",
            )
            for module in modules:
                self.assertTrue(
                    module.startswith("tests.test_")
                )
                module_path = (
                    PROJECT_ROOT
                    / (module.replace(".", "/") + ".py")
                )
                self.assertTrue(
                    module_path.is_file(),
                    msg=f"Eksik test modülü: {module}",
                )

    def test_performance_limits_are_explicit(self):
        self.assertEqual(
            PERFORMANCE_LIMITS,
            {
                "median_ms": 50.0,
                "p95_ms": 150.0,
                "max_ms": 300.0,
            },
        )

    def test_database_performance_probe_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            sandbox_db = Path(temp) / "acceptance.db"
            shutil.copy2(LIVE_DB, sandbox_db)
            before = hashlib.sha256(
                sandbox_db.read_bytes()
            ).hexdigest()

            result = database_performance_probe(
                sandbox_db,
                iterations=25,
            )

            after = hashlib.sha256(
                sandbox_db.read_bytes()
            ).hexdigest()

            self.assertEqual(before, after)
            self.assertTrue(result["passed"])
            self.assertLessEqual(
                result["median_ms"],
                PERFORMANCE_LIMITS["median_ms"],
            )
            self.assertLessEqual(
                result["p95_ms"],
                PERFORMANCE_LIMITS["p95_ms"],
            )
            self.assertLessEqual(
                result["max_ms"],
                PERFORMANCE_LIMITS["max_ms"],
            )
            self.assertEqual(result["iterations"], 25)
            self.assertEqual(result["integrity"], "ok")
            self.assertEqual(
                result["foreign_key_violations"],
                0,
            )

    def test_release_artifacts_are_cryptographically_valid(self):
        if not DMG_PATH.is_file() or not MANIFEST_PATH.is_file():
            self.skipTest(
                "Yerel Mac 1.1 dağıtım çıktıları mevcut değil."
            )

        result = validate_release_artifacts(
            DMG_PATH,
            MANIFEST_PATH,
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["version"], APP_VERSION)
        self.assertEqual(result["build"], APP_BUILD)
        self.assertEqual(
            result["schema_version"],
            LATEST_SCHEMA_VERSION,
        )
        self.assertTrue(result["dmg_sha_matches"])

    def test_direct_script_execution_can_load_project(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(
                    PROJECT_ROOT
                    / "tools"
                    / "run_commercial_acceptance.py"
                ),
                "--help",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn(
            "ticari final kabul",
            completed.stdout,
        )

    def test_runner_is_available_without_execution(self):
        self.assertTrue(callable(run_commercial_acceptance))

    def test_acceptance_tool_does_not_embed_release_tag_write(self):
        source = (
            PROJECT_ROOT
            / "tools"
            / "run_commercial_acceptance.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("git tag", source)
        self.assertNotIn("git push", source)
        self.assertNotIn("INSERT INTO", source)
        self.assertNotIn("UPDATE ", source)
        self.assertNotIn("DELETE FROM", source)


if __name__ == "__main__":
    unittest.main()

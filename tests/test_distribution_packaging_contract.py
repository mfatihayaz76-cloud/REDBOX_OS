import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from application_metadata import (
    APP_BUILD,
    APP_VERSION,
)
from database.migrations import LATEST_SCHEMA_VERSION
from tools.build_macos_release import (
    create_fresh_install_database,
    release_artifact_names,
    release_document_paths,
    validate_distribution_database,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"


class DistributionPackagingContractTest(unittest.TestCase):

    def setUp(self):
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

    def tearDown(self):
        self.assertEqual(
            hashlib.sha256(LIVE_DB.read_bytes()).hexdigest(),
            self.live_sha,
        )

    def test_spec_never_bundles_live_database(self):
        spec = (
            PROJECT_ROOT / "REDBOX_OS.spec"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            '"database/redbox_os.db",',
            spec,
        )
        self.assertIn(
            "REDBOX_PACKAGED_DB",
            spec,
        )

    def test_fresh_install_database_contains_no_real_data(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "redbox_os.db"
            result = create_fresh_install_database(
                target
            )
            self.assertTrue(target.is_file())
            self.assertEqual(
                result["schema_version"],
                LATEST_SCHEMA_VERSION,
            )
            self.assertEqual(result["integrity"], "ok")
            self.assertEqual(
                result["foreign_key_violations"],
                [],
            )

            conn = sqlite3.connect(target)
            try:
                counts = {
                    table: conn.execute(
                        f'SELECT COUNT(*) FROM "{table}"'
                    ).fetchone()[0]
                    for table in (
                        "firma_profili",
                        "kullanici_hesaplari",
                        "personeller",
                        "urunler",
                        "receteler",
                        "uretim",
                        "paketleme",
                        "sevkiyat",
                        "lisans_kayitlari",
                        "lisans_dogrulama_kayitlari",
                    )
                }
            finally:
                conn.close()

            self.assertEqual(
                counts,
                {table: 0 for table in counts},
            )

    def test_distribution_database_validation_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "redbox_os.db"
            create_fresh_install_database(target)
            before = hashlib.sha256(
                target.read_bytes()
            ).hexdigest()
            status = validate_distribution_database(
                target
            )
            after = hashlib.sha256(
                target.read_bytes()
            ).hexdigest()

            self.assertEqual(before, after)
            self.assertEqual(
                status["schema_version"],
                LATEST_SCHEMA_VERSION,
            )
            self.assertEqual(
                status["integrity"],
                "ok",
            )
            self.assertEqual(
                status["foreign_key_violations"],
                [],
            )

    def test_release_names_include_version_and_build(self):
        names = release_artifact_names()
        expected = f"{APP_VERSION}-{APP_BUILD}"
        self.assertIn(expected, names["dmg"])
        self.assertTrue(names["dmg"].endswith(".dmg"))
        self.assertTrue(names["manifest"].endswith(".json"))

    def test_build_tool_is_import_safe(self):
        source = (
            PROJECT_ROOT
            / "tools"
            / "build_macos_release.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'if __name__ == "__main__":',
            source,
        )
        self.assertNotIn(
            "database/redbox_os.db",
            source,
        )
        self.assertNotIn("rm -rf", source)


    def test_release_documents_are_complete(self):
        paths = release_document_paths()
        self.assertEqual(len(paths), 5)

        for path in paths:
            self.assertTrue(path.is_file())
            content = path.read_text(encoding="utf-8")
            self.assertIn("REDBOX OS", content)
            self.assertGreater(len(content), 300)

        source = (
            PROJECT_ROOT
            / "tools"
            / "build_macos_release.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'documents_dir = dmg_stage / "Belgeler"',
            source,
        )


    def test_codesign_clears_extended_attributes_first(self):
        source = (
            PROJECT_ROOT
            / "tools"
            / "build_macos_release.py"
        ).read_text(encoding="utf-8")
        xattr_position = source.index(
            '"/usr/bin/xattr"'
        )
        codesign_position = source.index(
            '"/usr/bin/codesign"'
        )
        self.assertLess(
            xattr_position,
            codesign_position,
        )
        self.assertIn('"-crs"', source)


    def test_signing_and_dmg_run_in_local_temporary_area(self):
        source = (
            PROJECT_ROOT
            / "tools"
            / "build_macos_release.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "tempfile.TemporaryDirectory(",
            source,
        )
        self.assertIn(
            'prefix="redbox_macos_release_"',
            source,
        )
        self.assertIn(
            "signed_app = dmg_stage / names",
            source,
        )
        self.assertIn(
            "shutil.copy2(local_dmg, dmg_path)",
            source,
        )


if __name__ == "__main__":
    unittest.main()

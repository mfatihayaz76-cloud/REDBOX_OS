from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "REDBOX_License_Manager.spec"
MANAGER = ROOT / "tools" / "license_manager.py"


class LicenseManagerPackagingTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SPEC.is_file())
        self.spec_source = SPEC.read_text(encoding="utf-8")
        self.manager_source = MANAGER.read_text(encoding="utf-8")

    def test_separate_manager_bundle_is_defined(self):
        self.assertIn(
            'name="REDBOX License Manager.app"',
            self.spec_source,
        )
        self.assertIn(
            '"com.redboxgida.licensemanager"',
            self.spec_source,
        )
        self.assertIn(
            '["tools/license_manager.py"]',
            self.spec_source,
        )

    def test_manager_has_no_live_database(self):
        forbidden = (
            "database/redbox_os.db",
            "REDBOX_PACKAGED_DB",
            "packaged_database",
        )
        for value in forbidden:
            self.assertNotIn(value, self.spec_source)

    def test_manager_has_no_secret_material(self):
        forbidden = (
            "ed25519_private_encrypted.pem",
            "LICENSE_AUTHORITY/private",
            "REDBOX_OS_LICENSE_AUTHORITY/private",
            ".rbx1",
        )
        for value in forbidden:
            self.assertNotIn(value, self.spec_source)

    def test_manager_uses_runtime_authority_location(self):
        self.assertIn(
            'Path.home() / "REDBOX_OS_LICENSE_AUTHORITY"',
            self.manager_source,
        )
        self.assertIn(
            'show="●"',
            self.manager_source,
        )

    def test_customer_application_spec_is_not_reused(self):
        self.assertNotIn(
            'name="REDBOX OS.app"',
            self.spec_source,
        )
        self.assertNotIn(
            "licensing/public_keys.json",
            self.spec_source,
        )


if __name__ == "__main__":
    unittest.main()

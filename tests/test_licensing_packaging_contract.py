import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "REDBOX_OS.spec"
REGISTRY_PATH = ROOT / "licensing" / "public_keys.json"


class LicensingPackagingContractTest(unittest.TestCase):
    def setUp(self):
        self.source = SPEC_PATH.read_text(encoding="utf-8")
        ast.parse(self.source)

    def test_public_key_registry_is_packaged(self):
        self.assertTrue(REGISTRY_PATH.is_file())
        self.assertIn(
            '"licensing/public_keys.json"',
            self.source,
        )
        self.assertIn(
            '"licensing"',
            self.source,
        )

    def test_licensing_modules_are_packaged(self):
        required = (
            "database.company_profile_engine",
            "database.licensing_engine",
            "ui.company_profile_window",
            "ui.license_center_window",
        )
        for module in required:
            self.assertIn(f'"{module}"', self.source)

    def test_ed25519_runtime_is_packaged(self):
        required = (
            "cryptography",
            "cryptography.hazmat.primitives.serialization",
            "cryptography.hazmat.primitives.asymmetric.ed25519",
        )
        for module in required:
            self.assertIn(f'"{module}"', self.source)

    def test_private_key_is_never_packaged(self):
        forbidden = (
            "REDBOX_OS_LICENSE_AUTHORITY",
            ".private.pem",
            "private_key",
            "Ed25519PrivateKey",
        )
        for expression in forbidden:
            self.assertNotIn(expression, self.source)

    def test_build_output_paths_are_not_datas(self):
        forbidden = (
            '"build/',
            '"dist/',
            '"release/',
        )
        for expression in forbidden:
            self.assertNotIn(expression, self.source)


if __name__ == "__main__":
    unittest.main()

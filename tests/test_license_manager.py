import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives import serialization

from database.licensing_engine import (
    LICENSE_PREFIX,
    PRODUCT_CODE,
)
from tools.license_manager import (
    DEFAULT_KEY_ID,
    LicenseManagerApp,
    issue_license_file,
    load_license_request,
)


COMPANY_HASH = "a" * 64
DEVICE_HASH = "b" * 64


class LicenseManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.authority = self.root / "authority"
        self.private_dir = self.authority / "private"
        self.private_dir.mkdir(parents=True)
        self.password = "guvenli-test-parolasi"

        private_key = Ed25519PrivateKey.generate()
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                self.password.encode("utf-8")
            ),
        )
        (
            self.private_dir
            / f"{DEFAULT_KEY_ID}_ed25519_private_encrypted.pem"
        ).write_bytes(pem)

        self.request_path = self.root / "request.json"
        self.request = {
            "talep_surumu": 1,
            "urun_kodu": PRODUCT_CODE,
            "firma_parmak_izi_sha256": COMPANY_HASH,
            "cihaz_parmak_izi_sha256": DEVICE_HASH,
        }
        self.request_path.write_text(
            json.dumps(self.request),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_request_is_loaded_and_validated(self):
        loaded = load_license_request(self.request_path)
        self.assertEqual(
            loaded["firma_parmak_izi_sha256"],
            COMPANY_HASH,
        )

    def test_invalid_request_is_rejected(self):
        self.request["cihaz_parmak_izi_sha256"] = "bozuk"
        self.request_path.write_text(
            json.dumps(self.request),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            load_license_request(self.request_path)

    def test_perpetual_license_is_created(self):
        output = self.root / "customer.rbx1"
        payload = issue_license_file(
            request_path=self.request_path,
            output_path=output,
            authority_path=self.authority,
            key_id=DEFAULT_KEY_ID,
            license_type="SURESIZ",
            start_date="2026-07-22",
            end_date=None,
            grace_days=7,
            password=self.password,
        )
        self.assertTrue(output.is_file())
        self.assertTrue(
            output.read_text(encoding="utf-8").startswith(
                LICENSE_PREFIX + "."
            )
        )
        self.assertEqual(payload["lisans_turu"], "SURESIZ")
        self.assertIsNone(payload["bitis_tarihi"])

    def test_existing_output_is_never_overwritten(self):
        output = self.root / "customer.rbx1"
        output.write_text("koru", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            issue_license_file(
                request_path=self.request_path,
                output_path=output,
                authority_path=self.authority,
                key_id=DEFAULT_KEY_ID,
                license_type="SURESIZ",
                start_date="2026-07-22",
                end_date=None,
                grace_days=7,
                password=self.password,
            )
        self.assertEqual(
            output.read_text(encoding="utf-8"),
            "koru",
        )

    def test_manager_ui_contract(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "tools/license_manager.py"
        ).read_text(encoding="utf-8")
        self.assertTrue(issubclass(LicenseManagerApp, object))
        for label in (
            "LİSANS TALEBİ SEÇ",
            "SÜRESİZ",
            "SÜRELİ",
            "İMZALI LİSANS OLUŞTUR",
            "DOSYAYI FINDER’DA GÖSTER",
        ):
            self.assertIn(label, source)
        self.assertNotIn("REDBOX_OS_LICENSE_AUTHORITY/private/", source)
        self.assertNotIn("PRIVATE KEY", source)


if __name__ == "__main__":
    unittest.main()

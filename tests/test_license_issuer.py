import base64
import unittest
from datetime import date, datetime

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from database.licensing_engine import (
    lisans_anahtarini_dogrula,
)
from tools.license_issuer import (
    lisans_anahtari_uret,
)


class LicenseIssuerTest(unittest.TestCase):

    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        public_raw = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_keys = {
            "REDBOX-ISSUER-TEST": base64.b64encode(
                public_raw
            ).decode("ascii")
        }
        self.company_hash = "a" * 64
        self.device_hash = "b" * 64
        self.request = {
            "talep_surumu": 1,
            "urun_kodu": "REDBOX_OS",
            "firma_parmak_izi_sha256": self.company_hash,
            "cihaz_parmak_izi_sha256": self.device_hash,
        }

    def issue(self, license_type, end=None):
        return lisans_anahtari_uret(
            self.request,
            self.private_key,
            "REDBOX-ISSUER-TEST",
            license_type,
            "2026-07-21",
            bitis_tarihi=end,
            grace_period_gun=7,
            duzenlenme_zamani=datetime.fromisoformat(
                "2026-07-21T01:30:00+03:00"
            ),
            lisans_uuid="LIC-ISSUER-TEST",
        )

    def test_issued_timed_license_verifies(self):
        token, payload = self.issue(
            "SURELI",
            "2027-07-21",
        )
        result = lisans_anahtarini_dogrula(
            token,
            self.public_keys,
            self.company_hash,
            self.device_hash,
            simdi=date(2026, 7, 21),
        )
        self.assertTrue(result["gecerli"])
        self.assertEqual(result["durum"], "AKTIF")
        self.assertEqual(
            payload["lisans_uuid"],
            "LIC-ISSUER-TEST",
        )

    def test_issued_perpetual_license_verifies(self):
        token, payload = self.issue("SURESIZ")
        result = lisans_anahtarini_dogrula(
            token,
            self.public_keys,
            self.company_hash,
            self.device_hash,
            simdi=date(2036, 7, 21),
        )
        self.assertTrue(result["gecerli"])
        self.assertIsNone(payload["bitis_tarihi"])

    def test_wrong_request_product_is_rejected(self):
        self.request["urun_kodu"] = "WRONG"

        with self.assertRaises(ValueError):
            self.issue("SURESIZ")

    def test_invalid_date_contract_is_rejected(self):
        with self.assertRaises(ValueError):
            self.issue(
                "SURELI",
                "2026-07-20",
            )


if __name__ == "__main__":
    unittest.main()

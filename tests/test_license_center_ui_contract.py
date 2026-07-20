import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WINDOW_PATH = ROOT / "ui" / "license_center_window.py"
SYSTEM_PATH = ROOT / "ui" / "system.py"


class LicenseCenterUIContractTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            WINDOW_PATH.is_file(),
            "Lisans merkezi penceresi oluşturulmalıdır.",
        )
        self.window_source = WINDOW_PATH.read_text(encoding="utf-8")
        self.window_tree = ast.parse(self.window_source)
        self.system_source = SYSTEM_PATH.read_text(encoding="utf-8")

    def test_professional_license_center_exists(self):
        classes = {
            node.name
            for node in self.window_tree.body
            if isinstance(node, ast.ClassDef)
        }
        self.assertIn("LicenseCenterWindow", classes)
        self.assertIn("LİSANS MERKEZİ", self.window_source)
        self.assertIn("LİSANS DURUMU", self.window_source)
        self.assertIn("CİHAZ PARMAK İZİ", self.window_source)

    def test_status_detail_uses_screen_safe_wrapping(self):
        self.assertIn("wraplength=650", self.window_source)
        self.assertIn(
            "Lisans talebi ve aktivasyonundan önce gerçek",
            self.window_source,
        )

    def test_license_request_can_be_exported(self):
        self.assertIn(
            "lisans_talep_bilgilerini_getir",
            self.window_source,
        )
        self.assertIn("asksaveasfilename", self.window_source)
        self.assertIn("json.dumps", self.window_source)
        self.assertIn("LİSANS TALEBİNİ DIŞA AKTAR", self.window_source)

    def test_activation_uses_only_licensing_engine(self):
        self.assertIn("lisansi_aktive_et", self.window_source)
        forbidden = (
            "INSERT INTO lisans_",
            "UPDATE lisans_",
            "DELETE FROM lisans_",
        )
        for expression in forbidden:
            self.assertNotIn(expression, self.window_source)

    def test_activation_requires_explicit_confirmation(self):
        self.assertIn("CTkCheckBox", self.window_source)
        self.assertIn("askyesno", self.window_source)
        self.assertIn("Açık Onay Gerekli", self.window_source)

    def test_private_key_is_never_used_by_application_ui(self):
        forbidden = (
            "Ed25519PrivateKey",
            "private_key",
            "LICENSE_AUTHORITY",
            "getpass",
            "license_issuer",
        )
        for expression in forbidden:
            self.assertNotIn(expression, self.window_source)

    def test_raw_license_is_not_written_or_logged(self):
        self.assertNotIn("write_text(lisans_anahtari", self.window_source)
        self.assertNotIn("print(lisans_anahtari", self.window_source)
        self.assertNotIn("yeni_deger=lisans_anahtari", self.window_source)

    def test_company_profile_is_required_for_request(self):
        self.assertIn("FIRMA_PROFILI_GEREKLI", self.window_source)
        self.assertIn("Firma Profili Gerekli", self.window_source)

    def test_system_page_opens_license_center(self):
        self.assertIn(
            "from ui.license_center_window import LicenseCenterWindow",
            self.system_source,
        )
        self.assertIn("def license_center(self):", self.system_source)
        self.assertIn("LİSANS MERKEZİNİ AÇ", self.system_source)
        self.assertIn("command=self.license_center", self.system_source)


if __name__ == "__main__":
    unittest.main()

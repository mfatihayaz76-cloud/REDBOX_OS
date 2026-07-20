import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOGIN_PATH = ROOT / "ui" / "login.py"


class LoginLicenseRoutingTest(unittest.TestCase):
    def setUp(self):
        self.source = LOGIN_PATH.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_login_uses_license_access_decision(self):
        self.assertIn("lisans_erisim_karari", self.source)
        self.assertIn("cihaz_parmak_izi_olustur", self.source)
        self.assertIn(
            "lisans_acik_anahtarlarini_yukle",
            self.source,
        )

    def test_initial_setup_routing_is_preserved(self):
        self.assertIn("ilk_kurulum_gerekli_mi", self.source)
        self.assertIn("self._ilk_kurulum_formu()", self.source)
        self.assertIn("self._giris_formu()", self.source)

    def test_legacy_transition_allows_normal_login_warning(self):
        self.assertIn('== "GECIS_SURESI"', self.source)
        self.assertIn("Lisans Geçiş Süresi", self.source)
        self.assertIn("Normal kullanım devam eder.", self.source)

    def test_denied_access_opens_controlled_completion_flow(self):
        self.assertIn("CompanyProfileWindow(", self.source)
        self.assertIn("LicenseCenterWindow(", self.source)
        self.assertIn("self.wait_window(company_window)", self.source)
        self.assertIn("self.wait_window(license_window)", self.source)

    def test_invalid_license_never_sets_authenticated_user(self):
        gate_position = self.source.index(
            'if not current_license.get("erisim_izni"):'
        )
        assignment_position = self.source.index(
            "self.authenticated_user = authenticated_user"
        )
        self.assertLess(gate_position, assignment_position)
        self.assertIn(
            "if not self._lisans_tamamlama_akisi(",
            self.source,
        )
        self.assertIn(
            "Lisans Aktivasyonu Gerekli",
            self.source,
        )

    def test_license_decision_is_carried_to_application(self):
        self.assertIn(
            'authenticated_user["lisans_durumu"]',
            self.source,
        )

    def test_login_ui_does_not_write_license_tables_directly(self):
        forbidden = (
            "INSERT INTO lisans_",
            "UPDATE lisans_",
            "DELETE FROM lisans_",
        )
        for expression in forbidden:
            self.assertNotIn(expression, self.source)


if __name__ == "__main__":
    unittest.main()

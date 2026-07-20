import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app.py"
LOGIN_PATH = PROJECT_ROOT / "ui" / "login.py"


class LoginFirstSetupIntegrationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app_source = APP_PATH.read_text(encoding="utf-8")
        cls.login_source = LOGIN_PATH.read_text(encoding="utf-8")
        cls.login_tree = ast.parse(cls.login_source)

    def test_startup_runs_migrations_before_login(self):
        init_position = self.app_source.index(
            "init_database()"
        )
        login_position = self.app_source.index(
            "current_user = authenticate_user()"
        )
        self.assertLess(init_position, login_position)

    def test_login_uses_setup_engine_decision(self):
        required = (
            "ilk_kurulum_gerekli_mi",
            "FirstSetupWizard",
            "self._ilk_kurulum_gerekli_mi()",
            "on_complete=self._kurulum_tamamlandi",
            "oturum_id=self.oturum_id",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.login_source)

    def test_existing_account_uses_normal_login(self):
        flow = (
            "if self._ilk_kurulum_gerekli_mi():"
        )
        self.assertIn(flow, self.login_source)
        self.assertIn(
            "else:\n            self._giris_formu()",
            self.login_source,
        )

    def test_legacy_setup_writer_is_removed(self):
        forbidden = (
            "def _hesap_var_mi",
            "def _aktif_personeller",
            "def _ilk_hesabi_olustur",
            "YÖNETİCİ HESABINI OLUŞTUR",
            "os.urandom",
            "INSERT INTO kullanici_hesaplari",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, self.login_source)

    def test_company_and_mode_identity_are_visible(self):
        login_required = (
            "uygulama_kimligini_getir",
            "self.company_label",
            "self.mode_label",
            "self.application_context",
            "authenticated_user.update(",
        )
        for token in login_required:
            with self.subTest(token=token):
                self.assertIn(token, self.login_source)

        app_required = (
            "self.company_name",
            "self.usage_mode",
            "text=self.company_name",
            "text=self.usage_mode",
            'f"REDBOX OS — {self.company_name}"',
        )
        for token in app_required:
            with self.subTest(token=token):
                self.assertIn(token, self.app_source)

    def test_setup_form_uses_full_window_area(self):
        required = (
            "self.card.grid_rowconfigure(3, weight=1)",
            'sticky="nsew"',
            "self.form.grid_rowconfigure(0, weight=1)",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.login_source)

    def test_setup_window_is_resizable_and_screen_safe(self):
        required = (
            "self._window_width = 900",
            "self._window_height = 820",
            "self.minsize(760, 680)",
            "self.resizable(True, True)",
            "screen_width - 40",
            "screen_height - 90",
            'f"{width}x{height}+{x}+{y}"',
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.login_source)

    def test_wizard_completion_returns_to_login(self):
        required = (
            "def _kurulum_tamamlandi",
            "self._window_width = 520",
            "self._window_height = 650",
            "self.resizable(False, False)",
            "self._giris_formu()",
            "self.after(50, self._ortala)",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.login_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)

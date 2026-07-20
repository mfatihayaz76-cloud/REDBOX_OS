import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_PATH = PROJECT_ROOT / "ui" / "first_setup_wizard.py"


class FirstSetupWizardUIContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = UI_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_professional_wizard_exists(self):
        classes = {
            node.name
            for node in self.tree.body
            if isinstance(node, ast.ClassDef)
        }
        self.assertIn("FirstSetupWizard", classes)

    def test_required_steps_are_visible(self):
        required = (
            "Kullanım Modu",
            "Firma Bilgileri",
            "Ana Tesis",
            "İlk Yönetici",
            "Son Kontrol",
            "GERCEK",
            "DEMO",
            "KURULUMU TAMAMLA",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.source)

    def test_all_writes_use_first_setup_engine(self):
        self.assertIn(
            "ilk_kurulumu_tamamla",
            self.source,
        )
        forbidden = (
            "INSERT INTO",
            "UPDATE ",
            "DELETE FROM",
            "BEGIN IMMEDIATE",
            "commit(",
            "rollback(",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, self.source)

    def test_each_step_has_isolated_fresh_container(self):
        required = (
            "def _create_content",
            "self.content.destroy()",
            "self._create_content()",
            "def _configure_confirmation",
            "self.confirmation_checkbox.grid_remove()",
            "self.content.grid_columnconfigure(0, weight=1)",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.source)

        self.assertNotIn(
            "def _scroll_to_top",
            self.source,
        )

    def test_explicit_confirmation_is_fixed_outside_scroll(self):
        required = (
            "self.confirmation_checkbox",
            "self.confirmation_checkbox.grid()",
            "ctk.CTkCheckBox(",
            "Bilgileri kontrol ettim ve kurulum",
            "işlemini açıkça onaylıyorum.",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.source)

    def test_checkbox_uses_supported_customtkinter_arguments(self):
        tree = ast.parse(self.source)
        checkbox_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "CTkCheckBox"
        ]

        self.assertEqual(len(checkbox_calls), 1)

        keyword_names = {
            keyword.arg
            for keyword in checkbox_calls[0].keywords
        }
        self.assertNotIn(
            "wraplength",
            keyword_names,
        )

    def test_primary_facility_reuses_company_address(self):
        forbidden = (
            '"tesis_il"',
            '"tesis_ilce"',
            '"tesis_adres"',
            '"tesis_telefon"',
            '"tesis_eposta"',
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, self.source)

        required = (
            '"ulke": self._value("firma_ulke")',
            '"il": self._value("firma_il")',
            '"ilce": self._value("firma_ilce")',
            "Firma profiliyle aynı",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.source)

    def test_step_values_survive_widget_rebuilds(self):
        required = (
            "self.field_values = {}",
            "ctk.StringVar(",
            "textvariable=self.field_values[key]",
            "variable = self.field_values.get(key)",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.source)

        self.assertNotIn(
            "self.entries",
            self.source,
        )

    def test_explicit_confirmation_contract(self):
        required = (
            "acik_onay",
            "Açık Onay Gerekli",
            "messagebox.askyesno",
            "Bilgileri kontrol ettim",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.source)

    def test_engine_receives_full_identity(self):
        required = (
            '"ticari_unvan"',
            '"kisa_ad"',
            '"tesis_kodu"',
            '"tesis_adi"',
            '"tesis_turu"',
            '"ad_soyad"',
            '"kullanici_adi"',
            '"parola"',
            'kullanim_modu=data["kullanim_modu"]',
            "oturum_id=self.oturum_id",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.source)


if __name__ == "__main__":
    unittest.main(verbosity=2)

import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WINDOW_PATH = (
    PROJECT_ROOT
    / "ui"
    / "company_profile_window.py"
)
SYSTEM_PATH = PROJECT_ROOT / "ui" / "system.py"


class CompanyProfileUIContractTest(unittest.TestCase):

    def setUp(self):
        self.window_source = WINDOW_PATH.read_text(
            encoding="utf-8"
        )
        self.system_source = SYSTEM_PATH.read_text(
            encoding="utf-8"
        )

    def test_company_profile_window_exists(self):
        tree = ast.parse(self.window_source)
        classes = {
            node.name
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        }
        self.assertIn("CompanyProfileWindow", classes)

    def test_real_company_fields_are_visible(self):
        for label in (
            "Ticari Unvan *",
            "Firma Kısa Adı *",
            "Vergi Dairesi",
            "Vergi Numarası",
            "Ülke *",
            "İl",
            "İlçe",
            "Açık Adres",
            "Telefon",
            "E-posta",
        ):
            self.assertIn(label, self.window_source)

    def test_all_writes_use_company_profile_engine(self):
        self.assertIn(
            "legacy_firma_profilini_olustur(",
            self.window_source,
        )
        self.assertNotIn(
            "INSERT INTO",
            self.window_source.upper(),
        )
        self.assertNotIn(
            "UPDATE firma_profili",
            self.window_source,
        )

    def test_explicit_confirmation_is_required(self):
        self.assertIn(
            "CTkCheckBox(",
            self.window_source,
        )
        self.assertIn(
            "askyesno(",
            self.window_source,
        )
        self.assertIn(
            "if not self.confirmed.get():",
            self.window_source,
        )

    def test_system_page_uses_dynamic_company_window(self):
        self.assertIn(
            "CompanyProfileWindow(",
            self.system_source,
        )
        self.assertNotIn(
            '("FİRMA / İŞLETME", "REDBOX GIDA")',
            self.system_source,
        )
        self.assertNotIn(
            '("ÜRÜN / MARKA", "LONG POTATO")',
            self.system_source,
        )

    def test_checkbox_uses_supported_arguments(self):
        tree = ast.parse(self.window_source)

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "CTkCheckBox"
            ):
                keywords = {
                    item.arg
                    for item in node.keywords
                }
                self.assertNotIn(
                    "wraplength",
                    keywords,
                )


if __name__ == "__main__":
    unittest.main()

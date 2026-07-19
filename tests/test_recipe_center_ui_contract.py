import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app.py"
UI_PATH = PROJECT_ROOT / "ui" / "recipe_center.py"


class RecipeCenterUIContractTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app_source = APP_PATH.read_text(
            encoding="utf-8"
        )
        cls.ui_source = UI_PATH.read_text(
            encoding="utf-8"
        )
        cls.app_tree = ast.parse(cls.app_source)
        cls.ui_tree = ast.parse(cls.ui_source)

    def test_professional_window_exists(self):
        classes = {
            node.name
            for node in self.ui_tree.body
            if isinstance(node, ast.ClassDef)
        }

        self.assertIn(
            "RecipeCenterWindow",
            classes,
        )

    def test_ui_uses_read_only_catalog_engine(self):
        self.assertIn(
            "recete_katalogunu_getir",
            self.ui_source,
        )
        self.assertIn(
            "recete_katalog_ozeti",
            self.ui_source,
        )

        forbidden = (
            "INSERT INTO",
            "UPDATE receteler",
            "DELETE FROM",
            "commit(",
        )

        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(
                    token,
                    self.ui_source,
                )

    def test_search_status_and_mass_balance_visible(self):
        required = (
            "Katalog Arama",
            "TÜM DURUMLAR",
            "KÜTLE DENGESİ",
            "DİJİTAL ONAY",
            "SEÇİLİ ÜRÜNE GİT",
        )

        for token in required:
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.ui_source,
                )

    def test_controlled_approval_actions_visible(self):
        required = (
            "İNCELEMEYE GÖNDER",
            "DİJİTAL ONAYLA",
            "REDDET",
            "RecipeDecisionDialog",
        )

        for token in required:
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.ui_source,
                )

    def test_approval_engine_is_used(self):
        required = (
            "receteyi_incelemeye_gonder",
            "receteyi_dijital_onayla",
            "recete_onayini_reddet",
        )

        for token in required:
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.ui_source,
                )

    def test_ui_does_not_write_approval_sql_directly(self):
        forbidden = (
            "INSERT INTO dijital_onaylar",
            "UPDATE receteler",
            "BEGIN IMMEDIATE",
            "conn.commit",
        )

        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(
                    token,
                    self.ui_source,
                )

    def test_recipe_pdf_ui_contract(self):
        required = (
            "PDF REÇETE FÖYÜ",
            "create_selected_recipe_pdf",
            "recete_pdf_olustur",
            "denetim_kaydi_ekle",
            'islem="PDF_OLUSTURMA"',
            '["open", str(pdf_path.resolve())]',
            'side="bottom"',
            "table_frame.pack_forget()",
        )

        for token in required:
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.ui_source,
                )

    def test_app_integration_contract(self):
        required = (
            "from ui.recipe_center import RecipeCenterWindow",
            "def recete_profesyonel_merkez_ac",
            "def recete_katalog_urune_git",
            "PROFESYONEL KATALOG",
        )

        for token in required:
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.app_source,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

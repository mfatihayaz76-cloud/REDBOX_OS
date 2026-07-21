import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WINDOW_PATH = PROJECT_ROOT / "ui" / "prerequisite_programs_window.py"
QUALITY_PATH = PROJECT_ROOT / "ui" / "quality.py"
SPEC_PATH = PROJECT_ROOT / "REDBOX_OS.spec"


class PrerequisiteProgramsUIContractTest(unittest.TestCase):

    def test_professional_prp_center_exists(self):
        self.assertTrue(WINDOW_PATH.is_file())
        source = WINDOW_PATH.read_text(encoding="utf-8")
        self.assertIn("class PrerequisiteProgramsWindow", source)
        for title in (
            "ALERJEN YÖNETİMİ",
            "KALİBRASYON",
            "BAKIM VE ARIZA",
            "ZARARLI MÜCADELESİ",
            "EĞİTİM VE YETKİNLİK",
            "GIDA SAVUNMASI / TACCP",
            "GIDA SAHTECİLİĞİ / VACCP",
        ):
            self.assertIn(title, source)

    def test_quality_page_opens_prp_center(self):
        source = QUALITY_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "from ui.prerequisite_programs_window import",
            source,
        )
        self.assertIn("PRP MERKEZİ", source)
        self.assertIn("open_prp_center", source)

    def test_ui_uses_engine_for_writes(self):
        source = WINDOW_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "from database.prerequisite_programs_engine import",
            source,
        )
        self.assertIn("prp_programi_olustur", source)
        self.assertNotIn("INSERT INTO", source)
        self.assertNotIn("UPDATE ", source)
        self.assertNotIn("DELETE FROM", source)

    def test_window_uses_dynamic_application_database(self):
        source = WINDOW_PATH.read_text(encoding="utf-8")
        self.assertIn("from database.db import get_connection", source)
        self.assertNotIn("database/redbox_os.db", source)

    def test_prp_modules_are_packaged(self):
        source = SPEC_PATH.read_text(encoding="utf-8")
        self.assertIn(
            '"database.prerequisite_programs_engine"',
            source,
        )
        self.assertIn(
            '"ui.prerequisite_programs_window"',
            source,
        )


if __name__ == "__main__":
    unittest.main()

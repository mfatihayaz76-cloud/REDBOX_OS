import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WINDOW = ROOT / "ui" / "audit_intelligence_window.py"
QUALITY = ROOT / "ui" / "quality.py"
SPEC = ROOT / "REDBOX_OS.spec"


class AuditIntelligenceUIContractTest(unittest.TestCase):

    def test_professional_center_and_sections_exist(self):
        self.assertTrue(WINDOW.is_file())
        source = WINDOW.read_text(encoding="utf-8")
        self.assertIn("class AuditIntelligenceWindow", source)
        for title in (
            "İÇ DENETİM",
            "MÜŞTERİ ŞİKÂYETİ",
            "NUMUNE VE LABORATUVAR",
            "KARANTİNA / BLOKE / SERBEST",
            "YÖNETİMİN GÖZDEN GEÇİRMESİ",
            "TEDARİKÇİ RİSK PUANLAMA",
            "MOCK RECALL",
        ):
            self.assertIn(title, source)

    def test_quality_page_opens_center(self):
        source = QUALITY.read_text(encoding="utf-8")
        self.assertIn(
            "from ui.audit_intelligence_window import",
            source,
        )
        self.assertIn("DENETİM ZEKÂSI", source)
        self.assertIn("open_audit_intelligence", source)

    def test_ui_uses_engine_for_writes(self):
        source = WINDOW.read_text(encoding="utf-8")
        self.assertIn(
            "from database.audit_intelligence_engine import",
            source,
        )
        self.assertIn("ic_denetim_olustur", source)
        self.assertNotIn("INSERT INTO", source)
        self.assertNotIn("UPDATE ", source)
        self.assertNotIn("DELETE FROM", source)

    def test_dynamic_database_is_used(self):
        source = WINDOW.read_text(encoding="utf-8")
        self.assertIn("from database.db import get_connection", source)
        self.assertNotIn("database/redbox_os.db", source)

    def test_modules_are_packaged(self):
        source = SPEC.read_text(encoding="utf-8")
        self.assertIn(
            '"database.audit_intelligence_engine"',
            source,
        )
        self.assertIn(
            '"ui.audit_intelligence_window"',
            source,
        )


if __name__ == "__main__":
    unittest.main()

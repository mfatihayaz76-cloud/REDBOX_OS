import hashlib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"
WINDOW = PROJECT_ROOT / "ui" / "haccp_window.py"
QUALITY = PROJECT_ROOT / "ui" / "quality.py"
SPEC = PROJECT_ROOT / "REDBOX_OS.spec"


class HaccpUIContractTest(unittest.TestCase):

    def setUp(self):
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

    def tearDown(self):
        self.assertEqual(
            hashlib.sha256(
                LIVE_DB.read_bytes()
            ).hexdigest(),
            self.live_sha,
        )

    def test_professional_haccp_center_exists(self):
        source = WINDOW.read_text(encoding="utf-8")
        self.assertIn("class HaccpWindow", source)
        self.assertIn("CTkToplevel", source)
        self.assertIn("HACCP YÖNETİM MERKEZİ", source)
        self.assertIn("ÜRÜN VE PLAN KİMLİĞİ", source)
        self.assertIn("PROSES AKIŞI", source)
        self.assertIn("TEHLİKE ANALİZİ", source)
        self.assertIn("CCP / OPRP", source)
        self.assertIn("İZLEME VE SAPMA", source)
        self.assertIn("DOĞRULAMA VE REVİZYON", source)

    def test_ui_uses_haccp_engine_for_writes(self):
        source = WINDOW.read_text(encoding="utf-8")
        required = {
            "haccp_plani_olustur",
            "proses_adimi_ekle",
            "tehlike_olustur",
            "tehlike_degerlendir",
            "kontrol_noktasi_belirle",
            "kritik_limit_ekle",
            "izleme_plani_ekle",
            "sapma_kaydet",
            "dogrulama_kaydet",
            "plan_revizyonu_olustur",
        }
        for name in required:
            self.assertIn(name, source)

        self.assertNotIn("INSERT INTO", source)
        self.assertNotIn("UPDATE ", source)
        self.assertNotIn("DELETE FROM", source)

    def test_quality_page_opens_haccp_center(self):
        source = QUALITY.read_text(encoding="utf-8")
        self.assertIn(
            "from ui.haccp_window import HaccpWindow",
            source,
        )
        self.assertIn("def open_haccp_center", source)
        self.assertIn("HACCP MERKEZİ", source)
        self.assertIn(
            "command=self.open_haccp_center",
            source,
        )

    def test_haccp_modules_are_packaged(self):
        source = SPEC.read_text(encoding="utf-8")
        self.assertIn('"database.haccp_engine"', source)
        self.assertIn('"ui.haccp_window"', source)

    def test_window_reads_dynamic_application_database(self):
        source = WINDOW.read_text(encoding="utf-8")
        self.assertIn("get_connection", source)
        self.assertNotIn("database/redbox_os.db", source)


if __name__ == "__main__":
    unittest.main()

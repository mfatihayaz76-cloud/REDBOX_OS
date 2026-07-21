import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.migrations import run_migrations
from database.prerequisite_programs_engine import (
    alerjen_matrisi_kaydet,
    ekipman_kaydet,
    egitim_katilimi_kaydet,
    prp_aksiyonu_ekle,
    prp_kaydi_ekle,
    prp_programi_olustur,
    risk_degerlendir,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"
USER = {
    "id": 1,
    "hesap_id": 1,
    "personel_id": 1,
    "kullanici_adi": "gfs2_test",
    "ad_soyad": "GFS-2 Test",
}


class PrerequisiteProgramsEngineTest(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "gfs2.db"
        shutil.copy2(LIVE_DB, self.db_path)
        run_migrations(self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def _program(self, program_type="ALERJEN"):
        return prp_programi_olustur(
            self.conn,
            {
                "program_kodu": f"PRP-{program_type}",
                "program_turu": program_type,
                "baslik": f"{program_type} Programı",
                "kapsam": "Tesis geneli",
                "sorumlu_personel_id": 1,
                "baslangic_tarihi": "21.07.2026",
            },
            kullanici=USER,
            oturum_id="gfs2-session",
        )

    def test_program_creation_is_atomic_and_audited(self):
        program_id = self._program()
        row = self.conn.execute(
            "SELECT * FROM prp_programlari WHERE id = ?",
            (program_id,),
        ).fetchone()
        audit = self.conn.execute(
            """
            SELECT * FROM denetim_kayitlari
            WHERE modul = 'PRP'
              AND kayit_turu = 'PRP_PROGRAMI'
              AND kayit_id = ?
            """,
            (program_id,),
        ).fetchone()

        self.assertEqual(row["program_turu"], "ALERJEN")
        self.assertEqual(row["durum"], "TASLAK")
        self.assertIsNotNone(audit)

    def test_invalid_program_writes_nothing(self):
        before = self.conn.total_changes
        with self.assertRaises(ValueError):
            prp_programi_olustur(
                self.conn,
                {
                    "program_kodu": "",
                    "program_turu": "GECERSIZ",
                    "baslik": "",
                },
                kullanici=USER,
            )
        self.assertEqual(self.conn.total_changes, before)

    def test_record_and_action_are_linked_and_audited(self):
        program_id = self._program("KALIBRASYON")
        record_id = prp_kaydi_ekle(
            self.conn,
            program_id,
            {
                "kayit_turu": "KALIBRASYON_KONTROLU",
                "kayit_tarihi": "21.07.2026",
                "baslik": "Terazi kontrolü",
                "uygunsuzluk_var": True,
            },
            kullanici=USER,
        )
        action_id = prp_aksiyonu_ekle(
            self.conn,
            record_id,
            {
                "aksiyon": "Teraziyi yeniden kalibre et",
                "sorumlu_personel_id": 1,
                "hedef_tarih": "22.07.2026",
            },
            kullanici=USER,
        )

        action = self.conn.execute(
            "SELECT * FROM prp_aksiyonlari WHERE id = ?",
            (action_id,),
        ).fetchone()
        self.assertEqual(action["kayit_id"], record_id)
        self.assertEqual(action["durum"], "ACIK")

    def test_specialized_program_records(self):
        allergen_program = self._program("ALERJEN")
        allergen_id = alerjen_matrisi_kaydet(
            self.conn,
            allergen_program,
            {
                "urun_id": 1,
                "alerjen_kodu": "SUT",
                "icerir": True,
                "capraz_bulasma_riski": True,
                "kontrol_onlemi": "Hat temizliği",
                "etiket_beyani": "Süt içerir",
            },
            kullanici=USER,
        )

        calibration_program = self._program("KALIBRASYON")
        equipment_id = ekipman_kaydet(
            self.conn,
            calibration_program,
            {
                "ekipman_kodu": "TRZ-01",
                "ekipman_adi": "Kontrol terazisi",
                "ekipman_turu": "OLCUM",
                "durum": "AKTIF",
            },
            kullanici=USER,
        )

        training_program = self._program("EGITIM_YETKINLIK")
        training_id = egitim_katilimi_kaydet(
            self.conn,
            training_program,
            {
                "personel_id": 1,
                "egitim_kodu": "ALR-01",
                "egitim_adi": "Alerjen farkındalığı",
                "egitim_tarihi": "21.07.2026",
                "puan": 90,
                "yetkin": True,
            },
            kullanici=USER,
        )

        self.assertGreater(allergen_id, 0)
        self.assertGreater(equipment_id, 0)
        self.assertGreater(training_id, 0)

    def test_taccp_vaccp_risk_score_is_engine_computed(self):
        program_id = self._program("TACCP")
        risk_id = risk_degerlendir(
            self.conn,
            program_id,
            {
                "risk_turu": "TACCP",
                "varlik_veya_surec": "Hammadde kabulü",
                "tehdit_veya_zafiyet": "Kasıtlı bulaştırma",
                "olasilik": 4,
                "etki": 5,
                "risk_puani": 1,
                "kontrol_onlemleri": "Yetkili alan ve kamera",
            },
            kullanici=USER,
        )
        row = self.conn.execute(
            """
            SELECT risk_puani, durum
            FROM prp_risk_degerlendirmeleri
            WHERE id = ?
            """,
            (risk_id,),
        ).fetchone()

        self.assertEqual(row["risk_puani"], 20)
        self.assertEqual(row["durum"], "ACIK")


if __name__ == "__main__":
    unittest.main()

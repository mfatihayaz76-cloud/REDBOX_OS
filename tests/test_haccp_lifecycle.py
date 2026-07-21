import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.haccp_engine import (
    akis_dogrula,
    dogrulama_kaydet,
    haccp_plani_olustur,
    izleme_plani_ekle,
    kritik_limit_ekle,
    kontrol_noktasi_belirle,
    plan_revizyonu_olustur,
    plani_onayla,
    proses_adimi_ekle,
    sapma_kaydet,
    tehlike_degerlendir,
    tehlike_olustur,
)
from database.migrations import run_migrations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"
NOW = "2026-07-21T20:20:00+03:00"
USER = {
    "hesap_id": 1,
    "personel_id": 1,
    "kullanici_adi": "fatih",
    "ad_soyad": "Fatih Ayaz",
}


class HaccpLifecycleTest(unittest.TestCase):

    def setUp(self):
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "haccp.db"
        shutil.copy2(LIVE_DB, self.database)
        run_migrations(self.database)
        self.conn = sqlite3.connect(self.database)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.addCleanup(self.conn.close)

        self.product_id = self.conn.execute(
            "SELECT id FROM urunler ORDER BY id LIMIT 1"
        ).fetchone()["id"]
        self.personnel_id = self.conn.execute(
            "SELECT id FROM personeller ORDER BY id LIMIT 1"
        ).fetchone()["id"]

    def tearDown(self):
        self.assertEqual(
            hashlib.sha256(LIVE_DB.read_bytes()).hexdigest(),
            self.live_sha,
        )

    def _complete_control(self):
        plan_id = haccp_plani_olustur(
            self.conn,
            {
                "plan_kodu": "HACCP-LIFE-001",
                "urun_id": self.product_id,
                "ad": "Yaşam Döngüsü Planı",
                "urun_aciklamasi": "Paketli ürün",
                "amaclanan_kullanim": "Doğrudan tüketim",
                "hazirlayan_personel_id": self.personnel_id,
                "simdi": NOW,
            },
            kullanici=USER,
        )
        step_id = proses_adimi_ekle(
            self.conn,
            plan_id,
            {
                "adim_no": 1,
                "ad": "Isıl işlem",
                "simdi": NOW,
            },
            kullanici=USER,
        )
        hazard_id = tehlike_olustur(
            self.conn,
            {
                "tehlike_kodu": "BIO-LIFE-001",
                "ad": "Patojen",
                "tehlike_turu": "BIYOLOJIK",
                "aciklama": "Yetersiz ısıl işlem",
                "simdi": NOW,
            },
            kullanici=USER,
        )
        assessment_id = tehlike_degerlendir(
            self.conn,
            plan_id,
            step_id,
            hazard_id,
            {
                "olasilik": 4,
                "siddet": 5,
                "gerekce": "Yüksek risk",
                "kontrol_onlemleri": "Sıcaklık kontrolü",
                "simdi": NOW,
            },
            kullanici=USER,
        )
        control_id = kontrol_noktasi_belirle(
            self.conn,
            assessment_id,
            {
                "kontrol_kodu": "CCP-LIFE-01",
                "sinif": "CCP",
                "karar_gerekcesi": "Kritik kontrol",
                "simdi": NOW,
            },
            kullanici=USER,
        )
        kritik_limit_ekle(
            self.conn,
            control_id,
            {
                "parametre": "Merkez sıcaklığı",
                "operator": "MIN",
                "alt_limit": 75.0,
                "birim": "°C",
                "bilimsel_dayanak": "VAL-001",
                "simdi": NOW,
            },
            kullanici=USER,
        )
        return plan_id, control_id

    def test_monitoring_plan_is_required_for_approval(self):
        plan_id, control_id = self._complete_control()
        akis_dogrula(
            self.conn,
            plan_id,
            self.personnel_id,
            {"sonuc": "UYGUN", "simdi": NOW},
            kullanici=USER,
        )

        with self.assertRaises(ValueError):
            plani_onayla(
                self.conn,
                plan_id,
                self.personnel_id,
                kullanici=USER,
                simdi=NOW,
            )

        monitoring_id = izleme_plani_ekle(
            self.conn,
            control_id,
            {
                "izlenecek_parametre": "Merkez sıcaklığı",
                "yontem": "Kalibre prob",
                "siklik": "Her parti",
                "sorumlu_rol": "Üretim sorumlusu",
                "kayit_formu": "HACCP-FRM-01",
                "sapmada_yapilacaklar": (
                    "Ürünü bloke et ve CAPA başlat"
                ),
                "simdi": NOW,
            },
            kullanici=USER,
        )
        plani_onayla(
            self.conn,
            plan_id,
            self.personnel_id,
            kullanici=USER,
            simdi=NOW,
        )

        status = self.conn.execute(
            "SELECT durum FROM haccp_planlari WHERE id = ?",
            (plan_id,),
        ).fetchone()[0]
        self.assertGreater(monitoring_id, 0)
        self.assertEqual(status, "ONAYLI")

    def test_deviation_is_recorded_and_audited(self):
        _, control_id = self._complete_control()
        deviation_id = sapma_kaydet(
            self.conn,
            control_id,
            {
                "tespit_zamani": NOW,
                "tespit_degeri": "71 °C",
                "aciklama": "Kritik limit altı",
                "urun_karari": "BLOKE",
                "duzeltme": "Yeniden ısıl işlem",
                "kok_neden": "Prob yerleşimi",
                "sorumlu_personel_id": self.personnel_id,
                "simdi": NOW,
            },
            kullanici=USER,
        )

        row = self.conn.execute(
            """
            SELECT durum, urun_karari
            FROM haccp_sapmalari
            WHERE id = ?
            """,
            (deviation_id,),
        ).fetchone()
        audit = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM denetim_kayitlari
            WHERE modul = 'HACCP'
              AND kayit_turu = 'HACCP_SAPMASI'
              AND kayit_id = ?
            """,
            (deviation_id,),
        ).fetchone()[0]

        self.assertEqual(tuple(row), ("ACIK", "BLOKE"))
        self.assertEqual(audit, 1)

    def test_verification_and_revision_are_controlled(self):
        plan_id, control_id = self._complete_control()
        izleme_plani_ekle(
            self.conn,
            control_id,
            {
                "izlenecek_parametre": "Merkez sıcaklığı",
                "yontem": "Kalibre prob",
                "siklik": "Her parti",
                "sorumlu_rol": "Üretim sorumlusu",
                "kayit_formu": "HACCP-FRM-01",
                "sapmada_yapilacaklar": "Ürünü bloke et",
                "simdi": NOW,
            },
            kullanici=USER,
        )
        akis_dogrula(
            self.conn,
            plan_id,
            self.personnel_id,
            {"sonuc": "UYGUN", "simdi": NOW},
            kullanici=USER,
        )
        plani_onayla(
            self.conn,
            plan_id,
            self.personnel_id,
            kullanici=USER,
            simdi=NOW,
        )

        verification_id = dogrulama_kaydet(
            self.conn,
            plan_id,
            {
                "dogrulama_turu": "IC_DENETIM",
                "dogrulama_tarihi": NOW,
                "dogrulayan_personel_id": self.personnel_id,
                "sonuc": "UYGUN",
                "bulgular": "Plan etkin",
                "simdi": NOW,
            },
            kullanici=USER,
        )
        revision_id = plan_revizyonu_olustur(
            self.conn,
            plan_id,
            {
                "plan_kodu": "HACCP-LIFE-001-R2",
                "revizyon_nedeni": "Yıllık gözden geçirme",
                "hazirlayan_personel_id": self.personnel_id,
                "simdi": NOW,
            },
            kullanici=USER,
        )

        original = self.conn.execute(
            "SELECT durum FROM haccp_planlari WHERE id = ?",
            (plan_id,),
        ).fetchone()[0]
        revision = self.conn.execute(
            """
            SELECT revizyon_no, durum, onceki_plan_id
            FROM haccp_planlari
            WHERE id = ?
            """,
            (revision_id,),
        ).fetchone()

        self.assertGreater(verification_id, 0)
        self.assertEqual(original, "ARSIV")
        self.assertEqual(
            tuple(revision),
            (2, "TASLAK", plan_id),
        )


if __name__ == "__main__":
    unittest.main()

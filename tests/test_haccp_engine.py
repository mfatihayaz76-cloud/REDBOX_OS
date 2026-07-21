import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.haccp_engine import (
    akis_dogrula,
    haccp_plani_olustur,
    kritik_limit_ekle,
    kontrol_noktasi_belirle,
    plani_onayla,
    proses_adimi_ekle,
    tehlike_degerlendir,
    tehlike_olustur,
)
from database.migrations import run_migrations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"
NOW = "2026-07-21T20:10:00+03:00"
USER = {
    "hesap_id": 1,
    "personel_id": 1,
    "kullanici_adi": "fatih",
    "ad_soyad": "Fatih Ayaz",
}


class HaccpEngineTest(unittest.TestCase):

    def setUp(self):
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.database = (
            Path(self.temporary.name) / "haccp.db"
        )
        shutil.copy2(LIVE_DB, self.database)
        run_migrations(self.database)
        self.connection = sqlite3.connect(self.database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.addCleanup(self.connection.close)

        self.product_id = self.connection.execute(
            "SELECT id FROM urunler ORDER BY id LIMIT 1"
        ).fetchone()["id"]
        self.personnel_id = self.connection.execute(
            "SELECT id FROM personeller ORDER BY id LIMIT 1"
        ).fetchone()["id"]

    def tearDown(self):
        self.assertEqual(
            hashlib.sha256(
                LIVE_DB.read_bytes()
            ).hexdigest(),
            self.live_sha,
        )

    def _create_plan(self):
        return haccp_plani_olustur(
            self.connection,
            {
                "plan_kodu": "HACCP-TEST-001",
                "urun_id": self.product_id,
                "ad": "Test HACCP Planı",
                "urun_aciklamasi": (
                    "Tüketime hazır paketli ürün"
                ),
                "amaclanan_kullanim": (
                    "Doğrudan tüketim"
                ),
                "hedef_tuketici": "Genel tüketici",
                "kullanim_kisitlari": (
                    "Alerjen beyanı dikkate alınmalıdır"
                ),
                "hazirlayan_personel_id": self.personnel_id,
                "simdi": NOW,
            },
            kullanici=USER,
            oturum_id="haccp-test",
        )

    def test_plan_creation_is_atomic_and_audited(self):
        plan_id = self._create_plan()

        plan = self.connection.execute(
            """
            SELECT plan_kodu, durum, revizyon_no
            FROM haccp_planlari
            WHERE id = ?
            """,
            (plan_id,),
        ).fetchone()
        audit = self.connection.execute(
            """
            SELECT modul, islem, kayit_turu, kayit_id
            FROM denetim_kayitlari
            WHERE modul = 'HACCP'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        self.assertEqual(
            tuple(plan),
            ("HACCP-TEST-001", "TASLAK", 1),
        )
        self.assertEqual(
            tuple(audit),
            ("HACCP", "OLUSTURMA", "HACCP_PLANI", plan_id),
        )

    def test_risk_score_is_computed_by_engine(self):
        plan_id = self._create_plan()
        step_id = proses_adimi_ekle(
            self.connection,
            plan_id,
            {
                "adim_no": 1,
                "ad": "Isıl işlem",
                "aciklama": "Kontrollü ısı uygulaması",
                "simdi": NOW,
            },
            kullanici=USER,
        )
        hazard_id = tehlike_olustur(
            self.connection,
            {
                "tehlike_kodu": "BIO-TEST-001",
                "ad": "Patojen mikroorganizma",
                "tehlike_turu": "BIYOLOJIK",
                "aciklama": "Yetersiz ısıl işlem riski",
                "simdi": NOW,
            },
            kullanici=USER,
        )
        assessment_id = tehlike_degerlendir(
            self.connection,
            plan_id,
            step_id,
            hazard_id,
            {
                "olasilik": 4,
                "siddet": 5,
                "gerekce": "Yüksek gıda güvenliği etkisi",
                "kontrol_onlemleri": "Isıl işlem kontrolü",
                "simdi": NOW,
            },
            kullanici=USER,
        )

        assessment = self.connection.execute(
            """
            SELECT risk_puani, onemli_tehlike
            FROM haccp_tehlike_degerlendirmeleri
            WHERE id = ?
            """,
            (assessment_id,),
        ).fetchone()

        self.assertEqual(tuple(assessment), (20, 1))

    def test_control_point_and_limit_contract(self):
        plan_id = self._create_plan()
        step_id = proses_adimi_ekle(
            self.connection,
            plan_id,
            {
                "adim_no": 1,
                "ad": "Isıl işlem",
                "simdi": NOW,
            },
            kullanici=USER,
        )
        hazard_id = tehlike_olustur(
            self.connection,
            {
                "tehlike_kodu": "BIO-TEST-002",
                "ad": "Patojen",
                "tehlike_turu": "BIYOLOJIK",
                "aciklama": "Isıl işlem tehlikesi",
                "simdi": NOW,
            },
            kullanici=USER,
        )
        assessment_id = tehlike_degerlendir(
            self.connection,
            plan_id,
            step_id,
            hazard_id,
            {
                "olasilik": 3,
                "siddet": 5,
                "gerekce": "Önemli tehlike",
                "kontrol_onlemleri": "Sıcaklık ve süre",
                "simdi": NOW,
            },
            kullanici=USER,
        )
        control_id = kontrol_noktasi_belirle(
            self.connection,
            assessment_id,
            {
                "kontrol_kodu": "CCP-01",
                "sinif": "CCP",
                "karar_agaci_cevaplari": (
                    "Evet/Evet/Hayır/Evet"
                ),
                "karar_gerekcesi": (
                    "Sonraki adım tehlikeyi gideremez"
                ),
                "simdi": NOW,
            },
            kullanici=USER,
        )
        limit_id = kritik_limit_ekle(
            self.connection,
            control_id,
            {
                "parametre": "Ürün merkez sıcaklığı",
                "operator": "MIN",
                "alt_limit": 75.0,
                "birim": "°C",
                "bilimsel_dayanak": (
                    "Validasyon çalışması VAL-001"
                ),
                "simdi": NOW,
            },
            kullanici=USER,
        )

        row = self.connection.execute(
            """
            SELECT k.sinif, l.parametre, l.alt_limit
            FROM haccp_kontrol_noktalari AS k
            JOIN haccp_kritik_limitleri AS l
              ON l.kontrol_noktasi_id = k.id
            WHERE l.id = ?
            """,
            (limit_id,),
        ).fetchone()

        self.assertEqual(
            tuple(row),
            ("CCP", "Ürün merkez sıcaklığı", 75.0),
        )

    def test_plan_approval_requires_flow_verification(self):
        plan_id = self._create_plan()

        with self.assertRaises(ValueError):
            plani_onayla(
                self.connection,
                plan_id,
                self.personnel_id,
                kullanici=USER,
                simdi=NOW,
            )

        akis_dogrula(
            self.connection,
            plan_id,
            self.personnel_id,
            {
                "sonuc": "UYGUN",
                "bulgular": "Akış yerinde doğrulandı",
                "simdi": NOW,
            },
            kullanici=USER,
        )

        with self.assertRaises(ValueError):
            plani_onayla(
                self.connection,
                plan_id,
                self.personnel_id,
                kullanici=USER,
                simdi=NOW,
            )

    def test_invalid_input_writes_nothing(self):
        before = self.connection.execute(
            "SELECT COUNT(*) FROM haccp_planlari"
        ).fetchone()[0]

        with self.assertRaises(ValueError):
            haccp_plani_olustur(
                self.connection,
                {
                    "plan_kodu": "",
                    "urun_id": self.product_id,
                    "ad": "",
                    "urun_aciklamasi": "",
                    "amaclanan_kullanim": "",
                    "hazirlayan_personel_id": self.personnel_id,
                    "simdi": NOW,
                },
                kullanici=USER,
            )

        after = self.connection.execute(
            "SELECT COUNT(*) FROM haccp_planlari"
        ).fetchone()[0]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

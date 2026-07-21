import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.audit_intelligence_engine import (
    ic_denetim_olustur,
    laboratuvar_numunesi_kaydet,
    mock_recall_kaydet,
    musteri_sikayeti_kaydet,
    tedarikci_riski_degerlendir,
    urun_durumu_kaydet,
    yonetim_gozden_gecirme_kaydet,
)
from database.migrations import run_migrations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"
USER = {
    "id": 1,
    "hesap_id": 1,
    "personel_id": 1,
    "kullanici_adi": "gfs3_test",
    "ad_soyad": "GFS-3 Test",
}


class AuditIntelligenceEngineTest(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "gfs3.db"
        shutil.copy2(LIVE_DB, self.db_path)
        run_migrations(self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.supplier_id = self.conn.execute(
            "SELECT id FROM tedarikciler ORDER BY id LIMIT 1"
        ).fetchone()[0]

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def test_internal_audit_is_atomic_and_audited(self):
        audit_id = ic_denetim_olustur(
            self.conn,
            {
                "denetim_kodu": "ID-2026-001",
                "denetim_tarihi": "21.07.2026",
                "kapsam": "Üretim ve depo",
                "bas_denetci_personel_id": 1,
            },
            kullanici=USER,
        )
        audit_log = self.conn.execute(
            """
            SELECT id FROM denetim_kayitlari
            WHERE modul = 'GFS_DENETIM'
              AND kayit_turu = 'IC_DENETIM'
              AND kayit_id = ?
            """,
            (audit_id,),
        ).fetchone()
        self.assertIsNotNone(audit_log)

    def test_complaint_sample_and_product_disposition(self):
        complaint_id = musteri_sikayeti_kaydet(
            self.conn,
            {
                "sikayet_kodu": "MS-2026-001",
                "bildirim_tarihi": "21.07.2026",
                "urun_id": 1,
                "lot_kodu": "LOT-001",
                "kategori": "AMBALAJ",
                "aciklama": "Ambalaj hasarı",
                "onem_derecesi": "ORTA",
            },
            kullanici=USER,
        )
        sample_id = laboratuvar_numunesi_kaydet(
            self.conn,
            {
                "numune_kodu": "LAB-2026-001",
                "numune_tarihi": "21.07.2026",
                "numune_turu": "URUN",
                "urun_id": 1,
                "lot_kodu": "LOT-001",
                "analizler": "Mikrobiyoloji",
            },
            kullanici=USER,
        )
        disposition_id = urun_durumu_kaydet(
            self.conn,
            {
                "urun_id": 1,
                "lot_kodu": "LOT-001",
                "durum": "BLOKE",
                "karar_tarihi": "21.07.2026",
                "neden": "Analiz sonucu bekleniyor",
                "karar_veren_personel_id": 1,
            },
            kullanici=USER,
        )
        self.assertGreater(complaint_id, 0)
        self.assertGreater(sample_id, 0)
        self.assertGreater(disposition_id, 0)

    def test_management_review_and_supplier_score(self):
        review_id = yonetim_gozden_gecirme_kaydet(
            self.conn,
            {
                "toplanti_kodu": "YGG-2026-001",
                "toplanti_tarihi": "21.07.2026",
                "donem": "2026/Q3",
                "katilimcilar": "Genel Müdür, Kalite Müdürü",
                "gundem": "Gıda güvenliği performansı",
            },
            kullanici=USER,
        )
        risk_id = tedarikci_riski_degerlendir(
            self.conn,
            {
                "tedarikci_id": self.supplier_id,
                "degerlendirme_tarihi": "21.07.2026",
                "kalite_puani": 80,
                "teslimat_puani": 70,
                "gida_guvenligi_puani": 90,
                "toplam_risk_puani": 1,
            },
            kullanici=USER,
        )
        row = self.conn.execute(
            """
            SELECT toplam_risk_puani, risk_seviyesi
            FROM gfs_tedarikci_riskleri WHERE id = ?
            """,
            (risk_id,),
        ).fetchone()
        self.assertGreater(review_id, 0)
        self.assertEqual(row["toplam_risk_puani"], 82)
        self.assertEqual(row["risk_seviyesi"], "DUSUK")

    def test_mock_recall_metrics_are_computed(self):
        recall_id = mock_recall_kaydet(
            self.conn,
            {
                "test_kodu": "MR-2026-001",
                "test_tarihi": "21.07.2026",
                "urun_id": 1,
                "lot_kodu": "LOT-001",
                "baslangic_zamani": "21.07.2026 10:00:00",
                "bitis_zamani": "21.07.2026 10:45:00",
                "hedef_miktar": 100,
                "izlenen_miktar": 98,
            },
            kullanici=USER,
        )
        row = self.conn.execute(
            """
            SELECT sure_dakika, basari_orani, basarili
            FROM gfs_mock_recall_testleri WHERE id = ?
            """,
            (recall_id,),
        ).fetchone()
        self.assertEqual(row["sure_dakika"], 45)
        self.assertEqual(row["basari_orani"], 98)
        self.assertEqual(row["basarili"], 1)


if __name__ == "__main__":
    unittest.main()

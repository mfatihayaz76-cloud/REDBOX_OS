import json
import sqlite3
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.audit_engine import (
    ALLOWED_ACTIONS,
    denetim_kaydi_ekle,
    denetim_kayitlarini_getir,
    yeni_oturum_id,
)


AUDIT_SCHEMA_SQL = """
CREATE TABLE denetim_kayitlari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    olay_zamani TEXT NOT NULL,
    kullanici_id INTEGER,
    personel_id INTEGER,
    kullanici_adi TEXT,
    ad_soyad TEXT,
    modul TEXT NOT NULL,
    islem TEXT NOT NULL,
    kayit_turu TEXT,
    kayit_id INTEGER,
    aciklama TEXT,
    eski_deger_json TEXT,
    yeni_deger_json TEXT,
    oturum_id TEXT
);

CREATE INDEX idx_denetim_olay_zamani
ON denetim_kayitlari (olay_zamani);

CREATE INDEX idx_denetim_modul_islem
ON denetim_kayitlari (modul, islem);

CREATE INDEX idx_denetim_kayit
ON denetim_kayitlari (kayit_turu, kayit_id);

CREATE INDEX idx_denetim_kullanici
ON denetim_kayitlari (kullanici_id, olay_zamani);
"""


class AuditEngineContractTest(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(AUDIT_SCHEMA_SQL)
        self.user = {
            "hesap_id": 7,
            "personel_id": 11,
            "kullanici_adi": "fatih",
            "ad_soyad": "Fatih Ayaz",
        }

    def tearDown(self):
        self.conn.close()

    def test_full_record_contract_and_json(self):
        session_id = yeni_oturum_id()

        record_id = denetim_kaydi_ekle(
            self.conn,
            modul="uretim",
            islem="OLUSTURMA",
            kullanici=self.user,
            kayit_turu="uretim",
            kayit_id=25,
            aciklama="Üretim kaydı oluşturuldu.",
            eski_deger={"durum": "YOK"},
            yeni_deger={
                "durum": "OLUSTURULDU",
                "net_kg": 20.412,
            },
            oturum_id=session_id,
            olay_zamani="19.07.2026 13:45:00",
        )

        row = self.conn.execute(
            """
            SELECT *
            FROM denetim_kayitlari
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row["olay_zamani"], "19.07.2026 13:45:00")
        self.assertEqual(row["kullanici_id"], 7)
        self.assertEqual(row["personel_id"], 11)
        self.assertEqual(row["kullanici_adi"], "fatih")
        self.assertEqual(row["ad_soyad"], "Fatih Ayaz")
        self.assertEqual(row["modul"], "URETIM")
        self.assertEqual(row["islem"], "OLUSTURMA")
        self.assertEqual(row["kayit_turu"], "uretim")
        self.assertEqual(row["kayit_id"], 25)
        self.assertEqual(row["oturum_id"], session_id)
        self.assertEqual(
            json.loads(row["eski_deger_json"]),
            {"durum": "YOK"},
        )
        self.assertEqual(
            json.loads(row["yeni_deger_json"]),
            {
                "durum": "OLUSTURULDU",
                "net_kg": 20.412,
            },
        )

    def test_all_allowed_actions_are_accepted(self):
        for action in sorted(ALLOWED_ACTIONS):
            with self.subTest(action=action):
                denetim_kaydi_ekle(
                    self.conn,
                    modul="SISTEM",
                    islem=action,
                    kullanici=self.user,
                    aciklama=f"{action} sözleşme testi",
                )

        count = self.conn.execute(
            "SELECT COUNT(*) FROM denetim_kayitlari"
        ).fetchone()[0]

        self.assertEqual(count, len(ALLOWED_ACTIONS))

    def test_invalid_action_is_rejected_without_insert(self):
        with self.assertRaisesRegex(
            ValueError,
            "Geçersiz denetim işlemi",
        ):
            denetim_kaydi_ekle(
                self.conn,
                modul="SISTEM",
                islem="GECERSIZ_ISLEM",
                kullanici=self.user,
            )

        count = self.conn.execute(
            "SELECT COUNT(*) FROM denetim_kayitlari"
        ).fetchone()[0]

        self.assertEqual(count, 0)

    def test_empty_module_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "Denetim modülü boş olamaz",
        ):
            denetim_kaydi_ekle(
                self.conn,
                modul="   ",
                islem="OLUSTURMA",
                kullanici=self.user,
            )

    def test_filter_search_limit_and_order_contract(self):
        first_id = denetim_kaydi_ekle(
            self.conn,
            modul="URETIM",
            islem="OLUSTURMA",
            kullanici=self.user,
            kayit_turu="uretim",
            kayit_id=101,
            aciklama="Birinci üretim kaydı",
            olay_zamani="19.07.2026 13:46:00",
        )
        second_id = denetim_kaydi_ekle(
            self.conn,
            modul="URETIM",
            islem="SILME",
            kullanici=self.user,
            kayit_turu="uretim",
            kayit_id=102,
            aciklama="İkinci üretim kaydı",
            olay_zamani="19.07.2026 13:47:00",
        )
        denetim_kaydi_ekle(
            self.conn,
            modul="PAKETLEME",
            islem="OLUSTURMA",
            kullanici=self.user,
            kayit_turu="paketleme",
            kayit_id=201,
            aciklama="Paketleme kaydı",
        )

        production_rows = denetim_kayitlarini_getir(
            self.conn,
            modul="uretim",
        )

        self.assertEqual(
            [row["id"] for row in production_rows],
            [second_id, first_id],
        )

        delete_rows = denetim_kayitlarini_getir(
            self.conn,
            islem="silme",
            kullanici_adi="fatih",
        )

        self.assertEqual(len(delete_rows), 1)
        self.assertEqual(delete_rows[0]["kayit_id"], 102)

        search_rows = denetim_kayitlarini_getir(
            self.conn,
            arama="İkinci",
            limit=1,
        )

        self.assertEqual(len(search_rows), 1)
        self.assertEqual(search_rows[0]["id"], second_id)

    def test_transaction_rollback_removes_audit_with_business_work(self):
        self.conn.execute("BEGIN")

        denetim_kaydi_ekle(
            self.conn,
            modul="DEPO_KABUL",
            islem="OLUSTURMA",
            kullanici=self.user,
            kayit_turu="depo_kabul",
            kayit_id=301,
        )

        self.conn.rollback()

        count = self.conn.execute(
            "SELECT COUNT(*) FROM denetim_kayitlari"
        ).fetchone()[0]

        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

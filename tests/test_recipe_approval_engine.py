import sqlite3
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from database.recipe_approval_engine import (
    recete_icerik_sha256,
    recete_onayini_reddet,
    receteyi_dijital_onayla,
    receteyi_incelemeye_gonder,
)


SCHEMA = """
CREATE TABLE urunler (
    id INTEGER PRIMARY KEY,
    urun_kodu TEXT NOT NULL
);

CREATE TABLE personeller (
    id INTEGER PRIMARY KEY,
    ad_soyad TEXT NOT NULL
);

CREATE TABLE kullanici_hesaplari (
    id INTEGER PRIMARY KEY,
    personel_id INTEGER
);

CREATE TABLE receteler (
    id INTEGER PRIMARY KEY,
    ad TEXT NOT NULL,
    parti_teorik_kg REAL NOT NULL,
    aktif INTEGER NOT NULL DEFAULT 0,
    revizyon_no TEXT,
    gecerlilik_tarihi TEXT,
    revizyon_aciklamasi TEXT,
    olusturan_personel_id INTEGER,
    urun_id INTEGER,
    recete_kodu TEXT,
    proses_suyu_kg REAL NOT NULL DEFAULT 0,
    durum TEXT NOT NULL DEFAULT 'TASLAK',
    onaylayan_personel_id INTEGER,
    onay_zamani TEXT,
    icerik_sha256 TEXT
);

CREATE TABLE hammaddeler (
    id INTEGER PRIMARY KEY,
    ad TEXT NOT NULL
);

CREATE TABLE recete_kalemleri (
    id INTEGER PRIMARY KEY,
    recete_id INTEGER NOT NULL,
    hammadde_id INTEGER NOT NULL,
    miktar_kg REAL NOT NULL
);

CREATE TABLE dijital_onaylar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kaynak_turu TEXT NOT NULL,
    kaynak_id INTEGER NOT NULL,
    onay_turu TEXT NOT NULL,
    karar TEXT NOT NULL,
    kullanici_id INTEGER NOT NULL,
    personel_id INTEGER NOT NULL,
    kullanici_adi TEXT NOT NULL,
    ad_soyad TEXT NOT NULL,
    onay_zamani TEXT NOT NULL,
    aciklama TEXT,
    icerik_sha256 TEXT NOT NULL,
    oturum_id TEXT
);

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
"""


ADMIN_USER = {
    "hesap_id": 1,
    "personel_id": 1,
    "kullanici_adi": "fatih",
    "ad_soyad": "Fatih Ayaz",
    "yonetici": 1,
    "oturum_id": "session-admin",
}

NORMAL_USER = {
    "hesap_id": 2,
    "personel_id": 2,
    "kullanici_adi": "eda",
    "ad_soyad": "Eda Ayaz",
    "yonetici": 0,
    "oturum_id": "session-user",
}


class RecipeApprovalEngineTest(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

        self.conn.execute(
            """
            INSERT INTO urunler (
                id,
                urun_kodu
            )
            VALUES (1, 'LP001')
            """
        )

        self.conn.executemany(
            """
            INSERT INTO personeller (
                id,
                ad_soyad
            )
            VALUES (?, ?)
            """,
            (
                (1, "Fatih Ayaz"),
                (2, "Eda Ayaz"),
            ),
        )

        self.conn.executemany(
            """
            INSERT INTO kullanici_hesaplari (
                id,
                personel_id
            )
            VALUES (?, ?)
            """,
            (
                (1, 1),
                (2, 2),
            ),
        )

        self.conn.executemany(
            """
            INSERT INTO hammaddeler (
                id,
                ad
            )
            VALUES (?, ?)
            """,
            (
                (1, "Patates Unu"),
                (2, "Tuz"),
            ),
        )

        self.conn.executemany(
            """
            INSERT INTO receteler (
                id,
                ad,
                parti_teorik_kg,
                aktif,
                revizyon_no,
                gecerlilik_tarihi,
                revizyon_aciklamasi,
                olusturan_personel_id,
                urun_id,
                recete_kodu,
                proses_suyu_kg,
                durum
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    1,
                    "Long Potato Rev.02",
                    20.0,
                    0,
                    "02",
                    "20.07.2027",
                    "Yeni revizyon",
                    2,
                    1,
                    "LP001-REC",
                    10.0,
                    "TASLAK",
                ),
                (
                    2,
                    "Long Potato Rev.01",
                    20.0,
                    1,
                    "01",
                    "20.07.2027",
                    "Tarihsel aktif revizyon",
                    2,
                    1,
                    "LP001-REC",
                    10.0,
                    "AKTIF",
                ),
            ),
        )

        self.conn.executemany(
            """
            INSERT INTO recete_kalemleri (
                id,
                recete_id,
                hammadde_id,
                miktar_kg
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                (1, 1, 1, 9.5),
                (2, 1, 2, 0.5),
                (3, 2, 1, 9.5),
                (4, 2, 2, 0.5),
            ),
        )

        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_hash_is_deterministic(self):
        first = recete_icerik_sha256(
            self.conn,
            1,
        )
        second = recete_icerik_sha256(
            self.conn,
            1,
        )

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_draft_can_be_sent_to_review(self):
        result = receteyi_incelemeye_gonder(
            self.conn,
            1,
            ADMIN_USER,
            "Teknik incelemeye gönderildi.",
        )

        self.assertEqual(
            result["durum"],
            "INCELEMEDE",
        )

        row = self.conn.execute(
            """
            SELECT
                durum,
                aktif,
                icerik_sha256
            FROM receteler
            WHERE id = 1
            """
        ).fetchone()

        self.assertEqual(row["durum"], "INCELEMEDE")
        self.assertEqual(row["aktif"], 0)
        self.assertEqual(len(row["icerik_sha256"]), 64)

    def test_review_recipe_can_be_approved(self):
        receteyi_incelemeye_gonder(
            self.conn,
            1,
            ADMIN_USER,
            "İncelemeye gönderildi.",
        )

        result = receteyi_dijital_onayla(
            self.conn,
            1,
            ADMIN_USER,
            "Formül ve kütle dengesi onaylandı.",
        )

        self.assertEqual(result["durum"], "ONAYLI")

        approval = self.conn.execute(
            """
            SELECT *
            FROM dijital_onaylar
            WHERE kaynak_id = 1
            """
        ).fetchone()

        self.assertEqual(
            approval["karar"],
            "ONAYLANDI",
        )
        self.assertEqual(
            approval["icerik_sha256"],
            result["icerik_sha256"],
        )

    def test_workflow_status_does_not_change_content_hash(
        self,
    ):
        draft_hash = recete_icerik_sha256(
            self.conn,
            1,
        )

        receteyi_incelemeye_gonder(
            self.conn,
            1,
            ADMIN_USER,
            "İncelemeye gönderildi.",
        )

        review_hash = recete_icerik_sha256(
            self.conn,
            1,
        )

        receteyi_dijital_onayla(
            self.conn,
            1,
            ADMIN_USER,
            "İçerik onaylandı.",
        )

        approved_hash = recete_icerik_sha256(
            self.conn,
            1,
        )

        self.assertEqual(
            draft_hash,
            review_hash,
        )
        self.assertEqual(
            review_hash,
            approved_hash,
        )


    def test_historical_active_recipe_can_be_approved(self):
        result = receteyi_dijital_onayla(
            self.conn,
            2,
            ADMIN_USER,
            "Tarihsel aktif reçete doğrulandı.",
        )

        self.assertEqual(result["durum"], "AKTIF")

        recipe = self.conn.execute(
            """
            SELECT
                durum,
                aktif,
                onaylayan_personel_id,
                icerik_sha256
            FROM receteler
            WHERE id = 2
            """
        ).fetchone()

        self.assertEqual(recipe["durum"], "AKTIF")
        self.assertEqual(recipe["aktif"], 1)
        self.assertEqual(
            recipe["onaylayan_personel_id"],
            1,
        )
        self.assertEqual(
            len(recipe["icerik_sha256"]),
            64,
        )

    def test_review_can_be_rejected_to_draft(self):
        receteyi_incelemeye_gonder(
            self.conn,
            1,
            ADMIN_USER,
            "İncelemeye gönderildi.",
        )

        result = recete_onayini_reddet(
            self.conn,
            1,
            ADMIN_USER,
            "Tuz oranı yeniden değerlendirilmeli.",
        )

        self.assertEqual(result["durum"], "TASLAK")

        approval = self.conn.execute(
            """
            SELECT karar
            FROM dijital_onaylar
            WHERE kaynak_id = 1
            """
        ).fetchone()

        self.assertEqual(
            approval["karar"],
            "REDDEDILDI",
        )

    def test_non_admin_cannot_approve(self):
        with self.assertRaises(PermissionError):
            receteyi_dijital_onayla(
                self.conn,
                2,
                NORMAL_USER,
                "Onay denemesi.",
            )

        count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM dijital_onaylar
            """
        ).fetchone()[0]

        self.assertEqual(count, 0)

    def test_duplicate_content_approval_rejected(self):
        receteyi_dijital_onayla(
            self.conn,
            2,
            ADMIN_USER,
            "İlk onay.",
        )

        with self.assertRaises(ValueError):
            receteyi_dijital_onayla(
                self.conn,
                2,
                ADMIN_USER,
                "İkinci onay.",
            )

        count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM dijital_onaylar
            WHERE kaynak_id = 2
            """
        ).fetchone()[0]

        self.assertEqual(count, 1)

    def test_audit_is_written_with_approval(self):
        receteyi_dijital_onayla(
            self.conn,
            2,
            ADMIN_USER,
            "Tarihsel kayıt onayı.",
        )

        audit = self.conn.execute(
            """
            SELECT
                modul,
                islem,
                kayit_turu,
                kayit_id
            FROM denetim_kayitlari
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        self.assertEqual(audit["modul"], "RECETE")
        self.assertEqual(
            audit["islem"],
            "DURUM_DEGISIKLIGI",
        )
        self.assertEqual(
            audit["kayit_turu"],
            "receteler",
        )
        self.assertEqual(audit["kayit_id"], 2)

    def test_failure_rolls_back_everything(self):
        self.conn.execute(
            """
            CREATE TRIGGER fail_recipe_approval
            BEFORE UPDATE ON receteler
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'forced approval failure'
                );
            END
            """
        )
        self.conn.commit()

        with self.assertRaises(sqlite3.DatabaseError):
            receteyi_dijital_onayla(
                self.conn,
                2,
                ADMIN_USER,
                "Rollback testi.",
            )

        approval_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM dijital_onaylar
            """
        ).fetchone()[0]

        audit_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM denetim_kayitlari
            """
        ).fetchone()[0]

        self.assertEqual(approval_count, 0)
        self.assertEqual(audit_count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

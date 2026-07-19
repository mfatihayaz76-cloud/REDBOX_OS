import sqlite3
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.migrations import (
    _migration_9_global_food_safety_foundation,
)


PREREQUISITE_SCHEMA = """
CREATE TABLE personeller (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_soyad TEXT NOT NULL
);

CREATE TABLE kullanici_hesaplari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personel_id INTEGER NOT NULL,
    kullanici_adi TEXT NOT NULL,
    FOREIGN KEY (personel_id)
        REFERENCES personeller(id)
);

CREATE TABLE kalite_uygunsuzluklari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baslik TEXT NOT NULL
);
"""


class GlobalFoodSafetyFoundationContractTest(
    unittest.TestCase
):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(PREREQUISITE_SCHEMA)

        self.conn.execute(
            """
            INSERT INTO personeller (
                id,
                ad_soyad
            )
            VALUES (1, 'Fatih Ayaz')
            """
        )
        self.conn.execute(
            """
            INSERT INTO kullanici_hesaplari (
                id,
                personel_id,
                kullanici_adi
            )
            VALUES (1, 1, 'fatih')
            """
        )
        self.conn.execute(
            """
            INSERT INTO kalite_uygunsuzluklari (
                id,
                baslik
            )
            VALUES (1, 'Test uygunsuzluğu')
            """
        )

        _migration_9_global_food_safety_foundation(
            self.conn
        )

    def tearDown(self):
        self.conn.close()

    def test_required_tables_and_indexes_exist(self):
        expected_tables = {
            "kontrollu_dokumanlar",
            "dokuman_revizyonlari",
            "dijital_onaylar",
            "kanit_dosyalari",
            "entegrasyon_cihazlari",
            "entegrasyon_olaylari",
        }

        expected_indexes = {
            "ux_dokuman_tek_onayli_revizyon",
            "idx_dokuman_revizyon_durum",
            "idx_kontrollu_dokuman_kategori",
            "idx_dijital_onay_kaynak",
            "idx_dijital_onay_personel",
            "idx_kanit_dosyasi_kaynak",
            "ux_kanit_dosyasi_kaynak_hash",
            "idx_entegrasyon_cihazi_tur_aktif",
            "idx_entegrasyon_olayi_durum",
            "idx_entegrasyon_olayi_cihaz",
            "idx_entegrasyon_olayi_uygunsuzluk",
        }

        actual_tables = {
            row[0]
            for row in self.conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

        actual_indexes = {
            row[0]
            for row in self.conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'index'
                """
            ).fetchall()
        }

        self.assertTrue(
            expected_tables.issubset(actual_tables)
        )
        self.assertTrue(
            expected_indexes.issubset(actual_indexes)
        )

    def test_document_approval_contract(self):
        document_id = self.conn.execute(
            """
            INSERT INTO kontrollu_dokumanlar (
                dokuman_kodu,
                baslik,
                kategori,
                dokuman_sahibi_personel_id,
                kayit_zamani,
                guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "HACCP-001",
                "HACCP Planı",
                "HACCP",
                1,
                "19.07.2026 14:30:00",
                "19.07.2026 14:30:00",
            ),
        ).lastrowid

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            self.conn.execute(
                """
                INSERT INTO dokuman_revizyonlari (
                    dokuman_id,
                    revizyon_no,
                    durum,
                    yayin_tarihi,
                    degisiklik_aciklamasi,
                    olusturan_personel_id,
                    kayit_zamani,
                    guncelleme_zamani
                )
                VALUES (?, ?, 'ONAYLI', ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    "00",
                    "19.07.2026",
                    "Eksik onay testi",
                    1,
                    "19.07.2026 14:31:00",
                    "19.07.2026 14:31:00",
                ),
            )

        self.conn.execute(
            """
            INSERT INTO dokuman_revizyonlari (
                dokuman_id,
                revizyon_no,
                durum,
                yayin_tarihi,
                degisiklik_aciklamasi,
                olusturan_personel_id,
                onaylayan_personel_id,
                onay_zamani,
                kayit_zamani,
                guncelleme_zamani
            )
            VALUES (
                ?, ?, 'ONAYLI', ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                document_id,
                "00",
                "19.07.2026",
                "İlk kontrollü yayın",
                1,
                1,
                "19.07.2026 14:32:00",
                "19.07.2026 14:31:00",
                "19.07.2026 14:32:00",
            ),
        )

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            self.conn.execute(
                """
                INSERT INTO dokuman_revizyonlari (
                    dokuman_id,
                    revizyon_no,
                    durum,
                    yayin_tarihi,
                    degisiklik_aciklamasi,
                    olusturan_personel_id,
                    onaylayan_personel_id,
                    onay_zamani,
                    kayit_zamani,
                    guncelleme_zamani
                )
                VALUES (
                    ?, ?, 'ONAYLI', ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    document_id,
                    "01",
                    "20.07.2026",
                    "İkinci aktif revizyon reddi",
                    1,
                    1,
                    "20.07.2026 10:00:00",
                    "20.07.2026 09:00:00",
                    "20.07.2026 10:00:00",
                ),
            )

    def test_digital_approval_identity_contract(self):
        approval_id = self.conn.execute(
            """
            INSERT INTO dijital_onaylar (
                kaynak_turu,
                kaynak_id,
                onay_turu,
                karar,
                kullanici_id,
                personel_id,
                kullanici_adi,
                ad_soyad,
                onay_zamani,
                icerik_sha256,
                oturum_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "DOKUMAN_REVIZYONU",
                10,
                "YAYIN_ONAYI",
                "ONAYLANDI",
                1,
                1,
                "fatih",
                "Fatih Ayaz",
                "19.07.2026 14:33:00",
                "a" * 64,
                "session-001",
            ),
        ).lastrowid

        row = self.conn.execute(
            """
            SELECT
                kullanici_adi,
                ad_soyad,
                karar,
                icerik_sha256
            FROM dijital_onaylar
            WHERE id = ?
            """,
            (approval_id,),
        ).fetchone()

        self.assertEqual(
            row,
            (
                "fatih",
                "Fatih Ayaz",
                "ONAYLANDI",
                "a" * 64,
            ),
        )

    def test_evidence_hash_uniqueness_contract(self):
        values = (
            "URETIM",
            25,
            "FOTOGRAF",
            "uretim_25.jpg",
            "evidence/uretim_25.jpg",
            "image/jpeg",
            2048,
            "b" * 64,
            1,
            1,
            "19.07.2026 14:34:00",
        )

        sql = """
            INSERT INTO kanit_dosyalari (
                kaynak_turu,
                kaynak_id,
                kanit_turu,
                dosya_adi,
                dosya_yolu,
                mime_turu,
                dosya_boyutu,
                dosya_sha256,
                yukleyen_kullanici_id,
                yukleyen_personel_id,
                kayit_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.conn.execute(sql, values)

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            self.conn.execute(sql, values)

    def test_device_and_event_json_contract(self):
        device_id = self.conn.execute(
            """
            INSERT INTO entegrasyon_cihazlari (
                cihaz_kodu,
                cihaz_adi,
                cihaz_turu,
                konum,
                yapilandirma_json,
                aktif,
                kayit_zamani,
                guncelleme_zamani
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                "CAM-URETIM-01",
                "Üretim Alanı Kamera 1",
                "KAMERA",
                "4. Kat Üretim",
                '{"fps": 10}',
                "19.07.2026 14:35:00",
                "19.07.2026 14:35:00",
            ),
        ).lastrowid

        event_id = self.conn.execute(
            """
            INSERT INTO entegrasyon_olaylari (
                olay_uuid,
                kaynak_turu,
                cihaz_id,
                olay_turu,
                olay_zamani,
                alinma_zamani,
                onem_derecesi,
                konum,
                payload_json,
                durum,
                kalite_uygunsuzluk_id,
                kayit_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "event-001",
                "KAMERA",
                device_id,
                "HIJYEN_UYGUNSUZLUGU",
                "19.07.2026 14:36:00",
                "19.07.2026 14:36:01",
                "YUKSEK",
                "4. Kat Üretim",
                '{"bone": false}',
                "YENI",
                1,
                "19.07.2026 14:36:01",
            ),
        ).lastrowid

        row = self.conn.execute(
            """
            SELECT
                kaynak_turu,
                olay_turu,
                onem_derecesi,
                durum,
                kalite_uygunsuzluk_id
            FROM entegrasyon_olaylari
            WHERE id = ?
            """,
            (event_id,),
        ).fetchone()

        self.assertEqual(
            row,
            (
                "KAMERA",
                "HIJYEN_UYGUNSUZLUGU",
                "YUKSEK",
                "YENI",
                1,
            ),
        )

        with self.assertRaises(
            sqlite3.IntegrityError
        ):
            self.conn.execute(
                """
                INSERT INTO entegrasyon_olaylari (
                    olay_uuid,
                    kaynak_turu,
                    olay_turu,
                    olay_zamani,
                    alinma_zamani,
                    payload_json,
                    kayit_zamani
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "event-invalid-json",
                    "SENSOR",
                    "SICAKLIK",
                    "19.07.2026 14:37:00",
                    "19.07.2026 14:37:01",
                    "{invalid-json}",
                    "19.07.2026 14:37:01",
                ),
            )

    def test_foreign_keys_and_integrity(self):
        violations = self.conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        integrity = self.conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        self.assertEqual(violations, [])
        self.assertEqual(integrity, "ok")


if __name__ == "__main__":
    unittest.main(verbosity=2)

import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.company_profile_engine import (
    firma_profilini_getir,
    legacy_firma_profilini_olustur,
)
from database.migrations import run_migrations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"


class CompanyProfileEngineTest(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = (
            Path(self.temp_dir.name)
            / "company_profile.db"
        )
        shutil.copy2(LIVE_DB, self.db_path)
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()
        run_migrations(self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = OFF")
        self.conn.execute(
            "DELETE FROM lisans_dogrulama_kayitlari"
        )
        self.conn.execute("DELETE FROM lisans_kayitlari")
        self.conn.execute("DELETE FROM demo_durumu")
        self.conn.execute("DELETE FROM ilk_kurulum_durumu")
        self.conn.execute("DELETE FROM tesis_profilleri")
        self.conn.execute("DELETE FROM firma_profili")
        self.conn.execute(
            """
            DELETE FROM denetim_kayitlari
            WHERE kayit_turu = 'firma_profili_legacy'
            """
        )
        self.conn.commit()
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.company = {
            "ticari_unvan": "Test Gıda Sanayi A.Ş.",
            "kisa_ad": "Test Gıda",
            "vergi_dairesi": "Kadıköy",
            "vergi_no": "1234567890",
            "ulke": "Türkiye",
            "il": "İstanbul",
            "ilce": "Kadıköy",
            "adres": "Test üretim adresi",
            "telefon": "+90 212 000 00 00",
            "eposta": "bilgi@testgida.example",
        }

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def create(self):
        return legacy_firma_profilini_olustur(
            self.conn,
            self.company,
            kullanici={
                "hesap_id": 1,
                "kullanici_adi": "fatih",
                "ad_soyad": "Fatih Ayaz",
            },
            oturum_id="com2-company-profile",
            simdi="2026-07-21T01:30:00+03:00",
        )

    def test_atomic_legacy_company_profile_creation(self):
        result = self.create()
        stored = firma_profilini_getir(self.conn)
        audit = self.conn.execute(
            """
            SELECT
                modul,
                islem,
                kayit_turu,
                kayit_id,
                oturum_id
            FROM denetim_kayitlari
            WHERE kayit_turu = 'firma_profili_legacy'
            """
        ).fetchone()

        self.assertEqual(
            result["ticari_unvan"],
            "Test Gıda Sanayi A.Ş.",
        )
        self.assertEqual(result, stored)
        self.assertEqual(
            audit,
            (
                "SISTEM",
                "OLUSTURMA",
                "firma_profili_legacy",
                1,
                "com2-company-profile",
            ),
        )

    def test_second_company_profile_is_rejected(self):
        self.create()

        with self.assertRaises(RuntimeError):
            self.create()

        count = self.conn.execute(
            "SELECT COUNT(*) FROM firma_profili"
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_invalid_company_writes_nothing(self):
        self.company["ticari_unvan"] = " "

        with self.assertRaises(ValueError):
            self.create()

        counts = (
            self.conn.execute(
                "SELECT COUNT(*) FROM firma_profili"
            ).fetchone()[0],
            self.conn.execute(
                """
                SELECT COUNT(*)
                FROM denetim_kayitlari
                WHERE kayit_turu = 'firma_profili_legacy'
                """
            ).fetchone()[0],
        )
        self.assertEqual(counts, (0, 0))

    def test_audit_failure_rolls_back_company(self):
        self.conn.execute(
            """
            CREATE TRIGGER com2_block_company_audit
            BEFORE INSERT ON denetim_kayitlari
            WHEN NEW.kayit_turu = 'firma_profili_legacy'
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'forced company audit failure'
                );
            END
            """
        )
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            self.create()

        count = self.conn.execute(
            "SELECT COUNT(*) FROM firma_profili"
        ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_live_database_is_not_modified(self):
        after_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()
        self.assertEqual(after_sha, self.live_sha)


if __name__ == "__main__":
    unittest.main()

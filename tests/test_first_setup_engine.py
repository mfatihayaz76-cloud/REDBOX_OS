import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.first_setup_engine import (
    ILK_YONETICI_YETKILERI,
    ilk_kurulum_bilgilerini_getir,
    ilk_kurulum_gerekli_mi,
    ilk_kurulumu_tamamla,
    uygulama_kimligini_getir,
)
from database.migrations import run_migrations


class FirstSetupEngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.live_db = cls.root / "database" / "redbox_os.db"
        cls.live_sha = hashlib.sha256(
            cls.live_db.read_bytes()
        ).hexdigest()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sandbox_db = (
            Path(self.temp_dir.name)
            / "redbox_os_com1_setup.db"
        )
        shutil.copy2(self.live_db, self.sandbox_db)
        run_migrations(self.sandbox_db)

        cleanup = sqlite3.connect(self.sandbox_db)
        try:
            cleanup.execute(
                "DELETE FROM kullanici_hesaplari"
            )
            cleanup.execute(
                "DELETE FROM ilk_kurulum_durumu"
            )
            cleanup.execute(
                "DELETE FROM tesis_profilleri"
            )
            cleanup.execute(
                "DELETE FROM firma_profili"
            )
            cleanup.commit()
        finally:
            cleanup.close()

        self.conn = sqlite3.connect(self.sandbox_db)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()
        self.assertEqual(
            hashlib.sha256(
                self.live_db.read_bytes()
            ).hexdigest(),
            self.live_sha,
        )

    def setup_data(self):
        return (
            {
                "ticari_unvan": "REDBOX GIDA SANAYİ",
                "kisa_ad": "REDBOX GIDA",
                "ulke": "Türkiye",
                "il": "İstanbul",
            },
            {
                "tesis_kodu": "IST-01",
                "tesis_adi": "Ana Üretim Tesisi",
                "tesis_turu": "URETIM",
                "ulke": "Türkiye",
                "il": "İstanbul",
            },
            {
                "ad_soyad": "COM1 Test Yönetici",
                "gorev": "Sistem Yöneticisi",
                "kullanici_adi": "com1.admin",
                "parola": "Guvenli-2026",
            },
        )

    def test_application_identity_before_and_after_setup(self):
        before = uygulama_kimligini_getir(self.conn)

        self.assertEqual(
            before["firma_kisa_ad"],
            "REDBOX OS",
        )
        self.assertEqual(
            before["kullanim_modu"],
            "KURULUM",
        )
        self.assertFalse(before["kurulum_tamamlandi"])
        self.assertFalse(before["legacy_kimlik"])

        firma, tesis, yonetici = self.setup_data()
        ilk_kurulumu_tamamla(
            self.conn,
            firma,
            tesis,
            yonetici,
            kullanim_modu="DEMO",
        )

        after = uygulama_kimligini_getir(self.conn)

        self.assertEqual(
            after["firma_kisa_ad"],
            firma["kisa_ad"],
        )
        self.assertEqual(
            after["tesis_kodu"],
            tesis["tesis_kodu"],
        )
        self.assertEqual(
            after["kullanim_modu"],
            "DEMO",
        )
        self.assertTrue(after["kurulum_tamamlandi"])
        self.assertFalse(after["legacy_kimlik"])

    def test_atomic_first_setup_creates_full_contract(self):
        firma, tesis, yonetici = self.setup_data()

        self.assertTrue(
            ilk_kurulum_gerekli_mi(self.conn)
        )

        result = ilk_kurulumu_tamamla(
            self.conn,
            firma,
            tesis,
            yonetici,
            kullanim_modu="GERCEK",
            oturum_id="com1-test-session",
        )

        self.assertEqual(result["firma_id"], 1)
        self.assertEqual(result["yetki_sayisi"], 10)
        self.assertFalse(
            ilk_kurulum_gerekli_mi(self.conn)
        )

        setup = ilk_kurulum_bilgilerini_getir(
            self.conn
        )
        self.assertEqual(setup["tamamlandi"], 1)
        self.assertEqual(
            setup["ticari_unvan"],
            "REDBOX GIDA SANAYİ",
        )
        self.assertEqual(
            setup["tesis_kodu"],
            "IST-01",
        )
        self.assertEqual(
            setup["kullanici_adi"],
            "com1.admin",
        )

        permissions = {
            row["yetki_kodu"]
            for row in self.conn.execute("""
                SELECT yetki_kodu
                FROM personel_yetkileri
                WHERE personel_id = ?
                  AND aktif = 1
            """, (result["personel_id"],)).fetchall()
        }

        self.assertEqual(
            permissions,
            set(ILK_YONETICI_YETKILERI),
        )

        account = self.conn.execute("""
            SELECT
                yonetici,
                aktif,
                iterasyon,
                LENGTH(parola_hash) AS hash_length,
                LENGTH(parola_tuzu) AS salt_length
            FROM kullanici_hesaplari
            WHERE id = ?
        """, (result["hesap_id"],)).fetchone()

        self.assertEqual(account["yonetici"], 1)
        self.assertEqual(account["aktif"], 1)
        self.assertEqual(account["iterasyon"], 600000)
        self.assertEqual(account["hash_length"], 64)
        self.assertEqual(account["salt_length"], 32)

    def test_first_setup_is_single_use(self):
        firma, tesis, yonetici = self.setup_data()

        ilk_kurulumu_tamamla(
            self.conn,
            firma,
            tesis,
            yonetici,
        )

        with self.assertRaises(RuntimeError):
            ilk_kurulumu_tamamla(
                self.conn,
                firma,
                tesis,
                yonetici,
            )

        self.assertEqual(
            self.conn.execute(
                "SELECT COUNT(*) FROM firma_profili"
            ).fetchone()[0],
            1,
        )

    def test_setup_is_audited(self):
        firma, tesis, yonetici = self.setup_data()

        result = ilk_kurulumu_tamamla(
            self.conn,
            firma,
            tesis,
            yonetici,
            oturum_id="com1-audit-session",
        )

        audit = self.conn.execute("""
            SELECT
                kullanici_id,
                personel_id,
                kullanici_adi,
                modul,
                islem,
                kayit_turu,
                kayit_id,
                oturum_id
            FROM denetim_kayitlari
            WHERE kayit_turu = 'ilk_kurulum'
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        self.assertEqual(
            audit["kullanici_id"],
            result["hesap_id"],
        )
        self.assertEqual(audit["modul"], "SISTEM")
        self.assertEqual(audit["islem"], "OLUSTURMA")
        self.assertEqual(audit["kayit_id"], 1)
        self.assertEqual(
            audit["oturum_id"],
            "com1-audit-session",
        )

    def test_audit_failure_rolls_back_everything(self):
        firma, tesis, yonetici = self.setup_data()

        self.conn.execute("""
            CREATE TRIGGER com1_block_audit
            BEFORE INSERT ON denetim_kayitlari
            WHEN NEW.kayit_turu = 'ilk_kurulum'
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'forced audit failure'
                );
            END
        """)
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            ilk_kurulumu_tamamla(
                self.conn,
                firma,
                tesis,
                yonetici,
            )

        for table in (
            "firma_profili",
            "tesis_profilleri",
            "ilk_kurulum_durumu",
            "kullanici_hesaplari",
        ):
            count = self.conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            self.assertEqual(count, 0, table)

    def test_invalid_input_writes_nothing(self):
        firma, tesis, yonetici = self.setup_data()
        yonetici["parola"] = "kisa"

        with self.assertRaises(ValueError):
            ilk_kurulumu_tamamla(
                self.conn,
                firma,
                tesis,
                yonetici,
            )

        self.assertEqual(
            self.conn.execute(
                "SELECT COUNT(*) FROM firma_profili"
            ).fetchone()[0],
            0,
        )


if __name__ == "__main__":
    unittest.main()

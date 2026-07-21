import hashlib
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.backup_recovery_engine import (
    BackupRecoveryError,
    BackupValidationError,
    bekleyen_geri_yuklemeyi_uygula,
    dogrulanmis_yedek_olustur,
    geri_yuklemeyi_hazirla,
    veritabani_durumunu_getir,
)
from database.migrations import run_migrations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"


class BackupRestorePreparationTest(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.live_path = self.root / "live.db"
        self.source_path = self.root / "source.db"
        self.backup_dir = self.root / "backups"
        self.recovery_dir = self.root / "recovery"

        shutil.copy2(LIVE_DB, self.live_path)
        shutil.copy2(LIVE_DB, self.source_path)
        run_migrations(self.live_path)
        run_migrations(self.source_path)

        conn = sqlite3.connect(self.source_path)
        try:
            conn.execute(
                """
                UPDATE sistem_ayarlari
                SET deger = 'RESTORE_SOURCE'
                WHERE anahtar = (
                    SELECT anahtar
                    FROM sistem_ayarlari
                    ORDER BY anahtar
                    LIMIT 1
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

        self.source_backup = (
            dogrulanmis_yedek_olustur(
                self.source_path,
                self.backup_dir,
                yedek_turu="MANUEL",
                kullanici={
                    "hesap_id": 1,
                    "kullanici_adi": "fatih",
                },
                oturum_id="com3-restore-source",
                simdi="2026-07-21T05:00:00+03:00",
            )
        )
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

    def tearDown(self):
        self.temp_dir.cleanup()

    def prepare(self):
        return geri_yuklemeyi_hazirla(
            self.live_path,
            self.source_backup["backup_path"],
            self.source_backup["manifest_path"],
            self.backup_dir,
            self.recovery_dir,
            kullanici={
                "hesap_id": 1,
                "kullanici_adi": "fatih",
                "ad_soyad": "Fatih Ayaz",
            },
            oturum_id="com3-restore",
            simdi="2026-07-21T06:00:00+03:00",
        )

    def test_restore_preparation_preserves_live_database(self):
        before = hashlib.sha256(
            self.live_path.read_bytes()
        ).hexdigest()

        result = self.prepare()

        after = hashlib.sha256(
            self.live_path.read_bytes()
        ).hexdigest()

        self.assertTrue(result["hazirlandi"])
        self.assertEqual(before, after)
        self.assertTrue(
            Path(result["pending_path"]).is_file()
        )
        self.assertTrue(
            Path(result["request_path"]).is_file()
        )
        self.assertTrue(
            Path(result["safety_backup_path"]).is_file()
        )
        self.assertTrue(
            Path(result["safety_manifest_path"]).is_file()
        )

    def test_pending_restore_is_migrated_and_verified(self):
        result = self.prepare()
        pending_status = veritabani_durumunu_getir(
            result["pending_path"]
        )
        request = json.loads(
            Path(result["request_path"]).read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            pending_status["integrity"],
            "ok",
        )
        self.assertEqual(
            pending_status["foreign_key_violations"],
            0,
        )
        self.assertEqual(
            pending_status["schema_version"],
            13,
        )
        self.assertEqual(
            request["format"],
            "REDBOX_RESTORE_REQUEST_V1",
        )
        self.assertEqual(
            request["pending_sha256"],
            pending_status["sha256"],
        )
        self.assertNotIn(
            "absolute_live_path",
            request,
        )

    def test_tampered_selected_backup_writes_nothing(self):
        backup_path = Path(
            self.source_backup["backup_path"]
        )
        conn = sqlite3.connect(backup_path)
        try:
            conn.execute(
                """
                UPDATE sistem_ayarlari
                SET deger = 'TAMPERED'
                WHERE anahtar = (
                    SELECT anahtar
                    FROM sistem_ayarlari
                    LIMIT 1
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

        live_before = hashlib.sha256(
            self.live_path.read_bytes()
        ).hexdigest()

        with self.assertRaises(BackupValidationError):
            self.prepare()

        live_after = hashlib.sha256(
            self.live_path.read_bytes()
        ).hexdigest()

        self.assertEqual(live_before, live_after)
        self.assertFalse(self.recovery_dir.exists())

    def test_second_pending_request_is_rejected(self):
        self.prepare()

        with self.assertRaises(Exception):
            self.prepare()

    def test_real_live_database_is_not_modified(self):
        self.prepare()

        live_after = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

        self.assertEqual(self.live_sha, live_after)


    def apply(self):
        return bekleyen_geri_yuklemeyi_uygula(
            self.live_path,
            self.backup_dir,
            self.recovery_dir,
            simdi="2026-07-21T06:05:00+03:00",
        )

    def test_prepared_restore_is_applied_and_audited(self):
        self.prepare()
        result = self.apply()

        conn = sqlite3.connect(self.live_path)
        try:
            restored_value = conn.execute(
                """
                SELECT deger
                FROM sistem_ayarlari
                ORDER BY anahtar
                LIMIT 1
                """
            ).fetchone()[0]
            restore_record = conn.execute(
                """
                SELECT durum, oturum_id
                FROM geri_yukleme_kayitlari
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            backup_record = conn.execute(
                """
                SELECT yedek_turu, durum
                FROM yedekleme_kayitlari
                WHERE yedek_turu = 'GERI_YUKLEME_ONCESI'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            audit = conn.execute(
                """
                SELECT modul, islem, kayit_turu
                FROM denetim_kayitlari
                WHERE kayit_turu = 'database_restore'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertTrue(result["uygulandi"])
        self.assertEqual(
            restored_value,
            "RESTORE_SOURCE",
        )
        self.assertEqual(
            restore_record,
            ("TAMAMLANDI", "com3-restore"),
        )
        self.assertEqual(
            backup_record,
            ("GERI_YUKLEME_ONCESI", "BASARILI"),
        )
        self.assertEqual(
            audit,
            (
                "SISTEM",
                "GERI_YUKLEME",
                "database_restore",
            ),
        )
        self.assertFalse(
            (
                self.recovery_dir
                / "restore_request.json"
            ).exists()
        )
        self.assertFalse(
            (
                self.recovery_dir
                / "restore_pending.db"
            ).exists()
        )

    def test_tampered_pending_copy_preserves_live(self):
        self.prepare()
        pending = (
            self.recovery_dir / "restore_pending.db"
        )
        conn = sqlite3.connect(pending)
        try:
            conn.execute(
                """
                UPDATE sistem_ayarlari
                SET deger = 'PENDING_TAMPER'
                WHERE anahtar = (
                    SELECT anahtar
                    FROM sistem_ayarlari
                    LIMIT 1
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

        before = hashlib.sha256(
            self.live_path.read_bytes()
        ).hexdigest()

        with self.assertRaises(BackupValidationError):
            self.apply()

        after = hashlib.sha256(
            self.live_path.read_bytes()
        ).hexdigest()

        self.assertEqual(before, after)

    def test_restore_audit_failure_returns_to_safety(self):
        Path(
            self.source_backup["backup_path"]
        ).unlink()
        Path(
            self.source_backup["manifest_path"]
        ).unlink()

        conn = sqlite3.connect(self.source_path)
        try:
            conn.execute("""
                CREATE TRIGGER com3_block_restore_audit
                BEFORE INSERT ON denetim_kayitlari
                WHEN NEW.kayit_turu = 'database_restore'
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'forced restore audit failure'
                    );
                END
            """)
            conn.commit()
        finally:
            conn.close()

        self.source_backup = (
            dogrulanmis_yedek_olustur(
                self.source_path,
                self.backup_dir,
                yedek_turu="MANUEL",
                kullanici={
                    "hesap_id": 1,
                    "kullanici_adi": "fatih",
                },
                oturum_id="com3-restore-failure-source",
                simdi="2026-07-21T05:30:00+03:00",
            )
        )

        before_conn = sqlite3.connect(self.live_path)
        try:
            before_dump = tuple(
                before_conn.iterdump()
            )
        finally:
            before_conn.close()

        self.prepare()

        with self.assertRaises(BackupRecoveryError):
            self.apply()

        after_conn = sqlite3.connect(self.live_path)
        try:
            after_dump = tuple(
                after_conn.iterdump()
            )
        finally:
            after_conn.close()

        status = veritabani_durumunu_getir(
            self.live_path
        )

        self.assertEqual(before_dump, after_dump)
        self.assertEqual(status["integrity"], "ok")
        self.assertEqual(
            status["foreign_key_violations"],
            0,
        )

    def test_no_pending_request_is_a_noop(self):
        result = self.apply()

        self.assertFalse(result["uygulandi"])
        self.assertEqual(
            result["neden_kodu"],
            "BEKLEYEN_ISTEK_YOK",
        )


if __name__ == "__main__":
    unittest.main()

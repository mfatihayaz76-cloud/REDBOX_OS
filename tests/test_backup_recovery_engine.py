import hashlib
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.backup_recovery_engine import (
    BackupValidationError,
    dogrulanmis_yedek_olustur,
    manuel_yedek_olustur,
    veritabani_durumunu_getir,
    yedegi_dogrula,
)
from database.migrations import (
    LATEST_SCHEMA_VERSION,
    run_migrations,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"


class BackupRecoveryEngineTest(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "source.db"
        self.backup_dir = self.root / "backups"
        shutil.copy2(LIVE_DB, self.source)
        run_migrations(self.source)
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_backup(self):
        return dogrulanmis_yedek_olustur(
            self.source,
            self.backup_dir,
            yedek_turu="MANUEL",
            kullanici={
                "hesap_id": 1,
                "kullanici_adi": "fatih",
                "ad_soyad": "Fatih Ayaz",
            },
            oturum_id="com3-backup-test",
            simdi="2026-07-21T02:40:00+03:00",
        )

    def test_database_status_is_read_only_and_complete(self):
        before = hashlib.sha256(
            self.source.read_bytes()
        ).hexdigest()

        status = veritabani_durumunu_getir(self.source)

        after = hashlib.sha256(
            self.source.read_bytes()
        ).hexdigest()

        self.assertEqual(status["integrity"], "ok")
        self.assertEqual(status["foreign_key_violations"], 0)
        self.assertEqual(
            status["schema_version"],
            LATEST_SCHEMA_VERSION,
        )
        self.assertEqual(status["sha256"], before)
        self.assertGreater(status["size_bytes"], 0)
        self.assertEqual(before, after)

    def test_verified_backup_creates_database_and_manifest(self):
        result = self.create_backup()
        backup_path = Path(result["backup_path"])
        manifest_path = Path(result["manifest_path"])

        self.assertTrue(backup_path.is_file())
        self.assertTrue(manifest_path.is_file())
        self.assertEqual(result["backup_type"], "MANUEL")
        self.assertEqual(result["integrity"], "ok")
        self.assertEqual(result["foreign_key_violations"], 0)

        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["format"], "REDBOX_BACKUP_V1")
        self.assertEqual(manifest["backup_type"], "MANUEL")
        self.assertEqual(
            manifest["schema_version"],
            LATEST_SCHEMA_VERSION,
        )
        self.assertEqual(
            manifest["database_sha256"],
            hashlib.sha256(backup_path.read_bytes()).hexdigest(),
        )
        self.assertNotIn("absolute_source_path", manifest)

    def test_created_backup_passes_read_only_validation(self):
        result = self.create_backup()
        backup_path = Path(result["backup_path"])
        manifest_path = Path(result["manifest_path"])

        before = hashlib.sha256(
            backup_path.read_bytes()
        ).hexdigest()

        validation = yedegi_dogrula(
            backup_path,
            manifest_path,
        )

        after = hashlib.sha256(
            backup_path.read_bytes()
        ).hexdigest()

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["integrity"], "ok")
        self.assertEqual(validation["foreign_key_violations"], 0)
        self.assertEqual(before, after)

    def test_tampered_backup_is_rejected(self):
        result = self.create_backup()
        backup_path = Path(result["backup_path"])
        manifest_path = Path(result["manifest_path"])

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

        with self.assertRaises(BackupValidationError):
            yedegi_dogrula(
                backup_path,
                manifest_path,
            )

    def test_source_and_live_database_are_preserved(self):
        source_before = hashlib.sha256(
            self.source.read_bytes()
        ).hexdigest()

        self.create_backup()

        source_after = hashlib.sha256(
            self.source.read_bytes()
        ).hexdigest()
        live_after = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

        self.assertEqual(source_before, source_after)
        self.assertEqual(self.live_sha, live_after)


    def test_manual_backup_is_recorded_and_audited(self):
        conn = sqlite3.connect(self.source)
        conn.execute("PRAGMA foreign_keys = ON")

        try:
            result = manuel_yedek_olustur(
                conn,
                self.source,
                self.backup_dir,
                kullanici={
                    "hesap_id": 1,
                    "kullanici_adi": "fatih",
                    "ad_soyad": "Fatih Ayaz",
                },
                oturum_id="com3-manual",
                simdi="2026-07-21T07:00:00+03:00",
            )
            record = conn.execute(
                """
                SELECT yedek_turu, durum, oturum_id
                FROM yedekleme_kayitlari
                WHERE yedek_uuid = ?
                """,
                (result["yedek_uuid"],),
            ).fetchone()
            audit = conn.execute(
                """
                SELECT modul, islem, kayit_turu
                FROM denetim_kayitlari
                WHERE kayit_id = ?
                  AND kayit_turu = 'database_backup'
                """,
                (result["kayit_id"],),
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(
            record,
            ("MANUEL", "BASARILI", "com3-manual"),
        )
        self.assertEqual(
            audit,
            (
                "SISTEM",
                "YEDEKLEME",
                "database_backup",
            ),
        )
        self.assertTrue(
            Path(result["backup_path"]).is_file()
        )
        self.assertTrue(
            Path(result["manifest_path"]).is_file()
        )

    def test_manual_backup_audit_failure_removes_files(self):
        conn = sqlite3.connect(self.source)
        conn.execute("PRAGMA foreign_keys = ON")

        try:
            conn.execute("""
                CREATE TRIGGER com3_block_manual_audit
                BEFORE INSERT ON denetim_kayitlari
                WHEN NEW.kayit_turu = 'database_backup'
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'forced manual audit failure'
                    );
                END
            """)
            conn.commit()

            with self.assertRaises(sqlite3.IntegrityError):
                manuel_yedek_olustur(
                    conn,
                    self.source,
                    self.backup_dir,
                    kullanici={
                        "hesap_id": 1,
                        "kullanici_adi": "fatih",
                    },
                    oturum_id="com3-manual-failure",
                    simdi="2026-07-21T07:00:00+03:00",
                )

            record_count = conn.execute(
                "SELECT COUNT(*) FROM yedekleme_kayitlari"
            ).fetchone()[0]
        finally:
            conn.close()

        files = (
            list(self.backup_dir.iterdir())
            if self.backup_dir.exists()
            else []
        )

        self.assertEqual(record_count, 0)
        self.assertEqual(files, [])

    def test_manual_backup_rejects_wrong_connection(self):
        other = self.root / "other.db"
        shutil.copy2(self.source, other)
        conn = sqlite3.connect(self.source)

        try:
            with self.assertRaises(Exception):
                manuel_yedek_olustur(
                    conn,
                    other,
                    self.backup_dir,
                    kullanici=None,
                    oturum_id="com3-wrong-manual",
                    simdi="2026-07-21T07:00:00+03:00",
                )
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()

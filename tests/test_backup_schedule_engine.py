import hashlib
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.backup_recovery_engine import (
    otomatik_yedek_gerekli_mi,
    otomatik_yedeklemeyi_calistir,
    saklama_politikasini_uygula,
    yedekleme_politikasini_getir,
    yedekleme_politikasini_guncelle,
)
from database.migrations import run_migrations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"


class BackupScheduleEngineTest(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / "schedule.db"
        shutil.copy2(LIVE_DB, self.db_path)
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

        fixture = sqlite3.connect(self.db_path)
        try:
            fixture.execute("PRAGMA foreign_keys = OFF")
            fixture.execute(
                "DELETE FROM yedekleme_kayitlari"
            )
            fixture.execute(
                "DELETE FROM yedekleme_politikasi"
            )
            fixture.execute(
                """
                DELETE FROM schema_migrations
                WHERE version = 13
                """
            )
            fixture.commit()
        finally:
            fixture.close()

        run_migrations(self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.user = {
            "hesap_id": 1,
            "kullanici_adi": "fatih",
            "ad_soyad": "Fatih Ayaz",
        }

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def update(self, **overrides):
        values = {
            "aktif": True,
            "siklik_saat": 12,
            "saklama_adedi": 7,
            "kullanici": self.user,
            "oturum_id": "com3-schedule",
            "simdi": "2026-07-21T03:00:00+03:00",
        }
        values.update(overrides)

        return yedekleme_politikasini_guncelle(
            self.conn,
            **values,
        )

    def test_default_policy_is_available(self):
        policy = yedekleme_politikasini_getir(
            self.conn
        )

        self.assertTrue(policy["aktif"])
        self.assertEqual(policy["siklik_saat"], 24)
        self.assertEqual(policy["saklama_adedi"], 14)

    def test_new_install_is_due_for_first_backup(self):
        decision = otomatik_yedek_gerekli_mi(
            self.conn,
            simdi="2026-07-21T03:00:00+03:00",
        )

        self.assertTrue(decision["gerekli"])
        self.assertEqual(
            decision["neden_kodu"],
            "YEDEK_ZAMANI_GELDI",
        )

    def test_policy_update_is_atomic_and_audited(self):
        policy = self.update()
        audit = self.conn.execute(
            """
            SELECT modul, islem, kayit_turu, oturum_id
            FROM denetim_kayitlari
            WHERE kayit_turu = 'yedekleme_politikasi'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        self.assertTrue(policy["aktif"])
        self.assertEqual(policy["siklik_saat"], 12)
        self.assertEqual(policy["saklama_adedi"], 7)
        self.assertEqual(
            policy["sonraki_otomatik_yedek_zamani"],
            "2026-07-21T15:00:00+03:00",
        )
        self.assertEqual(
            audit,
            (
                "SISTEM",
                "GUNCELLEME",
                "yedekleme_politikasi",
                "com3-schedule",
            ),
        )

    def test_inactive_policy_never_requests_backup(self):
        self.update(aktif=False)

        decision = otomatik_yedek_gerekli_mi(
            self.conn,
            simdi="2026-07-30T03:00:00+03:00",
        )

        self.assertFalse(decision["gerekli"])
        self.assertEqual(
            decision["neden_kodu"],
            "POLITIKA_PASIF",
        )

    def test_audit_failure_rolls_back_policy(self):
        before = yedekleme_politikasini_getir(
            self.conn
        )

        self.conn.execute("""
            CREATE TRIGGER com3_block_policy_audit
            BEFORE INSERT ON denetim_kayitlari
            WHEN NEW.kayit_turu = 'yedekleme_politikasi'
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'forced policy audit failure'
                );
            END
        """)
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            self.update()

        after = yedekleme_politikasini_getir(
            self.conn
        )

        self.assertEqual(
            after["siklik_saat"],
            before["siklik_saat"],
        )
        self.assertEqual(
            after["saklama_adedi"],
            before["saklama_adedi"],
        )

    def test_live_database_is_not_modified(self):
        self.update()

        live_after = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

        self.assertEqual(self.live_sha, live_after)


    def run_automatic(self, **overrides):
        values = {
            "kullanici": self.user,
            "oturum_id": "com3-automatic",
            "simdi": "2026-07-21T04:00:00+03:00",
        }
        values.update(overrides)

        return otomatik_yedeklemeyi_calistir(
            self.conn,
            self.db_path,
            self.root / "automatic_backups",
            **values,
        )

    def test_due_automatic_backup_is_recorded_and_audited(self):
        result = self.run_automatic()
        record = self.conn.execute(
            """
            SELECT
                yedek_turu,
                dosya_adi,
                manifest_dosya_adi,
                database_sha256,
                durum,
                oturum_id
            FROM yedekleme_kayitlari
            WHERE yedek_uuid = ?
            """,
            (result["yedek_uuid"],),
        ).fetchone()
        audit = self.conn.execute(
            """
            SELECT modul, islem, kayit_turu, oturum_id
            FROM denetim_kayitlari
            WHERE kayit_turu = 'database_backup'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        policy = yedekleme_politikasini_getir(
            self.conn
        )

        self.assertTrue(result["calisti"])
        self.assertTrue(
            Path(result["backup_path"]).is_file()
        )
        self.assertTrue(
            Path(result["manifest_path"]).is_file()
        )
        self.assertEqual(record[0], "OTOMATIK")
        self.assertEqual(
            record[1],
            Path(result["backup_path"]).name,
        )
        self.assertEqual(
            record[2],
            Path(result["manifest_path"]).name,
        )
        self.assertEqual(record[3], result["sha256"])
        self.assertEqual(record[4], "BASARILI")
        self.assertEqual(record[5], "com3-automatic")
        self.assertEqual(
            audit,
            (
                "SISTEM",
                "YEDEKLEME",
                "database_backup",
                "com3-automatic",
            ),
        )
        self.assertEqual(
            policy["son_otomatik_yedek_zamani"],
            "2026-07-21T04:00:00+03:00",
        )
        self.assertEqual(
            policy["sonraki_otomatik_yedek_zamani"],
            "2026-07-22T04:00:00+03:00",
        )

    def test_automatic_backup_is_skipped_before_due_time(self):
        first = self.run_automatic()
        second = self.run_automatic(
            simdi="2026-07-21T05:00:00+03:00",
        )

        records = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM yedekleme_kayitlari
            WHERE yedek_turu = 'OTOMATIK'
            """
        ).fetchone()[0]

        self.assertTrue(first["calisti"])
        self.assertFalse(second["calisti"])
        self.assertEqual(
            second["neden_kodu"],
            "HENUZ_ZAMANI_DEGIL",
        )
        self.assertEqual(records, 1)

    def test_automatic_backup_audit_failure_removes_files(self):
        self.conn.execute("""
            CREATE TRIGGER com3_block_backup_audit
            BEFORE INSERT ON denetim_kayitlari
            WHEN NEW.kayit_turu = 'database_backup'
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'forced backup audit failure'
                );
            END
        """)
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            self.run_automatic()

        backup_dir = self.root / "automatic_backups"
        files = (
            list(backup_dir.iterdir())
            if backup_dir.exists()
            else []
        )
        record_count = self.conn.execute(
            "SELECT COUNT(*) FROM yedekleme_kayitlari"
        ).fetchone()[0]
        policy = yedekleme_politikasini_getir(
            self.conn
        )

        self.assertEqual(files, [])
        self.assertEqual(record_count, 0)
        self.assertIsNone(
            policy["son_otomatik_yedek_zamani"]
        )

    def test_wrong_database_connection_is_rejected(self):
        other_path = self.root / "other.db"
        shutil.copy2(self.db_path, other_path)

        with self.assertRaises(Exception):
            otomatik_yedeklemeyi_calistir(
                self.conn,
                other_path,
                self.root / "automatic_backups",
                kullanici=self.user,
                oturum_id="com3-wrong-db",
                simdi="2026-07-21T04:00:00+03:00",
            )


    def create_three_automatic_backups(self):
        results = []

        for value in (
            "2026-07-21T04:00:00+03:00",
            "2026-07-22T04:00:00+03:00",
            "2026-07-23T04:00:00+03:00",
        ):
            results.append(
                self.run_automatic(simdi=value)
            )

        self.update(
            siklik_saat=24,
            saklama_adedi=2,
            simdi="2026-07-23T05:00:00+03:00",
        )
        return results

    def test_retention_keeps_newest_automatic_backups(self):
        results = self.create_three_automatic_backups()
        unrelated = (
            self.root
            / "automatic_backups"
            / "unrelated.txt"
        )
        unrelated.write_text(
            "korunmalı",
            encoding="utf-8",
        )

        retention = saklama_politikasini_uygula(
            self.conn,
            self.root / "automatic_backups",
            kullanici=self.user,
            oturum_id="com3-retention",
            simdi="2026-07-23T06:00:00+03:00",
        )

        statuses = self.conn.execute(
            """
            SELECT durum
            FROM yedekleme_kayitlari
            ORDER BY olusturma_zamani, id
            """
        ).fetchall()
        audit = self.conn.execute(
            """
            SELECT modul, islem, kayit_turu, oturum_id
            FROM denetim_kayitlari
            WHERE kayit_turu = 'backup_retention'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        self.assertEqual(
            retention["silinen_yedek_sayisi"],
            1,
        )
        self.assertFalse(
            Path(results[0]["backup_path"]).exists()
        )
        self.assertFalse(
            Path(results[0]["manifest_path"]).exists()
        )
        self.assertTrue(
            Path(results[1]["backup_path"]).is_file()
        )
        self.assertTrue(
            Path(results[2]["backup_path"]).is_file()
        )
        self.assertTrue(unrelated.is_file())
        self.assertEqual(
            statuses,
            [
                ("SILINDI",),
                ("BASARILI",),
                ("BASARILI",),
            ],
        )
        self.assertEqual(
            audit,
            (
                "SISTEM",
                "SILME",
                "backup_retention",
                "com3-retention",
            ),
        )

    def test_retention_audit_failure_restores_files(self):
        results = self.create_three_automatic_backups()

        self.conn.execute("""
            CREATE TRIGGER com3_block_retention_audit
            BEFORE INSERT ON denetim_kayitlari
            WHEN NEW.kayit_turu = 'backup_retention'
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'forced retention audit failure'
                );
            END
        """)
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            saklama_politikasini_uygula(
                self.conn,
                self.root / "automatic_backups",
                kullanici=self.user,
                oturum_id="com3-retention-failure",
                simdi="2026-07-23T06:00:00+03:00",
            )

        statuses = self.conn.execute(
            """
            SELECT durum
            FROM yedekleme_kayitlari
            ORDER BY olusturma_zamani, id
            """
        ).fetchall()

        for result in results:
            self.assertTrue(
                Path(result["backup_path"]).is_file()
            )
            self.assertTrue(
                Path(result["manifest_path"]).is_file()
            )

        self.assertEqual(
            statuses,
            [
                ("BASARILI",),
                ("BASARILI",),
                ("BASARILI",),
            ],
        )

    def test_retention_within_limit_changes_nothing(self):
        self.run_automatic()

        result = saklama_politikasini_uygula(
            self.conn,
            self.root / "automatic_backups",
            kullanici=self.user,
            oturum_id="com3-retention-noop",
            simdi="2026-07-21T05:00:00+03:00",
        )

        self.assertEqual(
            result["silinen_yedek_sayisi"],
            0,
        )


if __name__ == "__main__":
    unittest.main()

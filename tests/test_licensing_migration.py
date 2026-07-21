import hashlib
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
import unittest
from pathlib import Path

from database.migrations import (
    LATEST_SCHEMA_VERSION,
    MIGRATIONS,
    run_migrations,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = PROJECT_ROOT / "database" / "redbox_os.db"


class LicensingMigrationTest(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = (
            Path(self.temp_dir.name)
            / "licensing_migration.db"
        )
        shutil.copy2(LIVE_DB, self.db_path)
        self.live_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()

    def tearDown(self):
        self.temp_dir.cleanup()

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def test_migration_12_creates_licensing_contract(self):
        run_migrations(self.db_path)

        conn = self.connect()
        try:
            version = conn.execute(
                "PRAGMA user_version"
            ).fetchone()[0]
            migration = conn.execute(
                """
                SELECT name
                FROM schema_migrations
                WHERE version = 12
                """
            ).fetchone()
            tables = {
                row[0]
                for row in conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
            }
            license_count = conn.execute(
                "SELECT COUNT(*) FROM lisans_kayitlari"
            ).fetchone()[0]
            validation_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM lisans_dogrulama_kayitlari
                """
            ).fetchone()[0]
        finally:
            conn.close()

        self.assertGreaterEqual(LATEST_SCHEMA_VERSION, 12)
        self.assertEqual(version, LATEST_SCHEMA_VERSION)
        self.assertEqual(migration, ("licensing_foundation",))
        self.assertIn("lisans_kayitlari", tables)
        self.assertIn(
            "lisans_dogrulama_kayitlari",
            tables,
        )
        self.assertIn(
            "lisans_gecis_durumu",
            tables,
        )
        self.assertEqual(license_count, 0)
        self.assertEqual(validation_count, 0)

    def test_license_type_and_active_company_constraints(self):
        run_migrations(self.db_path)

        conn = self.connect()
        try:
            conn.execute(
                """
                INSERT INTO firma_profili (
                    id,
                    ticari_unvan,
                    kisa_ad,
                    kayit_zamani
                )
                VALUES (1, 'TEST GIDA A.Ş.', 'TEST', '2026-07-21')
                """
            )

            common = (
                "a" * 64,
                '{"lisans_uuid":"LIC-001"}',
                "c2lnbmF0dXJl",
                "REDBOX-PROD-1",
                "2026-07-21T01:00:00+03:00",
                "2026-07-21T01:00:00+03:00",
                "2026-07-21T01:00:00+03:00",
            )

            conn.execute(
                """
                INSERT INTO lisans_kayitlari (
                    lisans_uuid,
                    lisans_anahtari_sha256,
                    firma_id,
                    cihaz_parmak_izi_sha256,
                    lisans_turu,
                    baslangic_tarihi,
                    bitis_tarihi,
                    imzali_payload_json,
                    imza_base64,
                    acik_anahtar_kimligi,
                    aktivasyon_zamani,
                    kayit_zamani,
                    guncelleme_zamani
                )
                VALUES (
                    'LIC-001',
                    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                    1,
                    ?,
                    'SURELI',
                    '2026-07-21',
                    '2027-07-21',
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                common,
            )

            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO lisans_kayitlari (
                        lisans_uuid,
                        lisans_anahtari_sha256,
                        firma_id,
                        cihaz_parmak_izi_sha256,
                        lisans_turu,
                        baslangic_tarihi,
                        bitis_tarihi,
                        imzali_payload_json,
                        imza_base64,
                        acik_anahtar_kimligi,
                        aktivasyon_zamani,
                        kayit_zamani,
                        guncelleme_zamani
                    )
                    VALUES (
                        'LIC-002',
                        'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
                        1,
                        ?,
                        'SURELI',
                        '2026-07-21',
                        '2027-07-21',
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?
                    )
                    """,
                    common,
                )

            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO lisans_kayitlari (
                        lisans_uuid,
                        lisans_anahtari_sha256,
                        firma_id,
                        cihaz_parmak_izi_sha256,
                        lisans_turu,
                        baslangic_tarihi,
                        bitis_tarihi,
                        imzali_payload_json,
                        imza_base64,
                        acik_anahtar_kimligi,
                        aktivasyon_zamani,
                        kayit_zamani,
                        guncelleme_zamani
                    )
                    VALUES (
                        'LIC-003',
                        'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd',
                        1,
                        ?,
                        'SURELI',
                        '2026-07-21',
                        NULL,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?
                    )
                    """,
                    common,
                )
        finally:
            conn.close()

    def test_existing_install_receives_30_day_transition(self):
        run_migrations(self.db_path)

        conn = self.connect()
        try:
            transition = conn.execute(
                """
                SELECT
                    durum,
                    kaynak,
                    baslangic_zamani,
                    bitis_zamani,
                    gecis_suresi_gun
                FROM lisans_gecis_durumu
                WHERE id = 1
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(transition)
        self.assertEqual(transition[0], "AKTIF")
        self.assertEqual(
            transition[1],
            "LEGACY_UPGRADE",
        )
        self.assertEqual(transition[4], 30)

        start = datetime.fromisoformat(transition[2])
        end = datetime.fromisoformat(transition[3])
        self.assertEqual(
            end - start,
            timedelta(days=30),
        )

    def test_migration_12_is_idempotent(self):
        run_migrations(self.db_path)
        run_migrations(self.db_path)

        conn = self.connect()
        try:
            migration_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM schema_migrations
                WHERE version = 12
                """
            ).fetchone()[0]
            integrity = conn.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
            violations = conn.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
        finally:
            conn.close()

        self.assertEqual(migration_count, 1)
        self.assertEqual(integrity, "ok")
        self.assertEqual(violations, [])

    def test_migration_12_supports_minimal_legacy_schema(self):
        minimal_path = Path(self.temp_dir.name) / "minimal_legacy.db"
        conn = sqlite3.connect(minimal_path)
        try:
            conn.execute(
                """
                CREATE TABLE schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL
                )
                """
            )
            for version, name, _migration in MIGRATIONS:
                if version >= 12:
                    continue
                conn.execute(
                    """
                    INSERT INTO schema_migrations (
                        version,
                        name,
                        applied_at
                    )
                    VALUES (?, ?, 'test')
                    """,
                    (version, name),
                )
            conn.execute("PRAGMA user_version = 11")
            conn.commit()
        finally:
            conn.close()

        run_migrations(minimal_path)

        conn = sqlite3.connect(minimal_path)
        try:
            version = conn.execute(
                "PRAGMA user_version"
            ).fetchone()[0]
            license_tables = {
                row[0]
                for row in conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
            }
            transition_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM lisans_gecis_durumu
                """
            ).fetchone()[0]
            integrity = conn.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
        finally:
            conn.close()

        self.assertEqual(version, LATEST_SCHEMA_VERSION)
        self.assertTrue(
            {
                "lisans_kayitlari",
                "lisans_dogrulama_kayitlari",
                "lisans_gecis_durumu",
            }.issubset(license_tables)
        )
        self.assertEqual(transition_count, 0)
        self.assertEqual(integrity, "ok")

    def test_live_database_is_not_modified(self):
        after_sha = hashlib.sha256(
            LIVE_DB.read_bytes()
        ).hexdigest()
        self.assertEqual(after_sha, self.live_sha)


if __name__ == "__main__":
    unittest.main()

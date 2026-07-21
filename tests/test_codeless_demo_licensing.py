import sqlite3
import unittest
from datetime import datetime, timedelta, timezone

from database.licensing_engine import (
    DEMO_DURATION_DAYS,
    demo_baslat,
    demo_durumunu_getir,
    lisans_erisim_karari,
)
from database.migrations import (
    LATEST_SCHEMA_VERSION,
    _migration_17_codeless_demo,
)


UTC3 = timezone(timedelta(hours=3))
DEVICE_HASH = "a" * 64


class CodelessDemoLicensingTest(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(
            """
            CREATE TABLE ilk_kurulum_durumu (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                kullanim_modu TEXT NOT NULL
                    CHECK (kullanim_modu IN ('GERCEK', 'DEMO')),
                tamamlandi INTEGER NOT NULL
                    CHECK (tamamlandi IN (0, 1))
            );

            CREATE TABLE kullanici_hesaplari (
                id INTEGER PRIMARY KEY,
                aktif INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE lisans_kayitlari (
                id INTEGER PRIMARY KEY,
                durum TEXT NOT NULL
            );

            CREATE TABLE lisans_gecis_durumu (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                durum TEXT NOT NULL,
                baslangic_zamani TEXT NOT NULL,
                bitis_zamani TEXT NOT NULL,
                gecis_suresi_gun INTEGER NOT NULL
            );
            """
        )
        _migration_17_codeless_demo(self.conn)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def complete_setup(self, mode):
        self.conn.execute(
            """
            INSERT INTO ilk_kurulum_durumu (
                id,
                kullanim_modu,
                tamamlandi
            )
            VALUES (1, ?, 1)
            """,
            (mode,),
        )
        self.conn.execute(
            """
            INSERT INTO kullanici_hesaplari (id, aktif)
            VALUES (1, 1)
            """
        )
        self.conn.commit()

    def test_schema_17_and_demo_contract(self):
        self.assertGreaterEqual(LATEST_SCHEMA_VERSION, 17)
        self.assertEqual(DEMO_DURATION_DAYS, 30)

        columns = {
            row[1]
            for row in self.conn.execute(
                "PRAGMA table_info(demo_durumu)"
            ).fetchall()
        }
        self.assertEqual(
            columns,
            {
                "id",
                "durum",
                "baslangic_zamani",
                "bitis_zamani",
                "sure_gun",
                "son_guvenilir_zaman",
                "kayit_zamani",
                "guncelleme_zamani",
            },
        )

    def test_demo_setup_starts_without_license_key(self):
        self.complete_setup("DEMO")
        start = datetime(2026, 7, 21, 9, 0, tzinfo=UTC3)

        result = demo_baslat(self.conn, simdi=start)

        self.assertEqual(result["durum"], "DEMO_AKTIF")
        self.assertTrue(result["erisim_izni"])
        self.assertEqual(result["kalan_gun"], 30)
        self.assertNotIn("lisans_anahtari", str(result).lower())

        row = self.conn.execute(
            """
            SELECT sure_gun, baslangic_zamani, bitis_zamani
            FROM demo_durumu
            WHERE id = 1
            """
        ).fetchone()
        self.assertEqual(row[0], 30)
        self.assertEqual(
            datetime.fromisoformat(row[2])
            - datetime.fromisoformat(row[1]),
            timedelta(days=30),
        )

    def test_demo_start_is_idempotent(self):
        self.complete_setup("DEMO")
        start = datetime(2026, 7, 21, 9, 0, tzinfo=UTC3)

        first = demo_baslat(self.conn, simdi=start)
        second = demo_baslat(
            self.conn,
            simdi=start + timedelta(days=2),
        )

        self.assertEqual(
            first["baslangic_zamani"],
            second["baslangic_zamani"],
        )
        count = self.conn.execute(
            "SELECT COUNT(*) FROM demo_durumu"
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_real_mode_never_auto_starts_demo(self):
        self.complete_setup("GERCEK")

        with self.assertRaises(ValueError):
            demo_baslat(
                self.conn,
                simdi=datetime(2026, 7, 21, tzinfo=UTC3),
            )

        count = self.conn.execute(
            "SELECT COUNT(*) FROM demo_durumu"
        ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_active_and_expired_demo_decisions(self):
        self.complete_setup("DEMO")
        start = datetime(2026, 7, 21, 9, 0, tzinfo=UTC3)
        demo_baslat(self.conn, simdi=start)

        active = demo_durumunu_getir(
            self.conn,
            simdi=start + timedelta(days=10),
        )
        expired = demo_durumunu_getir(
            self.conn,
            simdi=start + timedelta(days=31),
        )

        self.assertTrue(active["erisim_izni"])
        self.assertEqual(active["durum"], "DEMO_AKTIF")
        self.assertEqual(active["kalan_gun"], 20)

        self.assertFalse(expired["erisim_izni"])
        self.assertEqual(expired["durum"], "DEMO_SURESI_DOLDU")
        self.assertEqual(
            expired["akis"],
            "LISANS_AKTIVASYONU",
        )

    def test_clock_rollback_is_rejected(self):
        self.complete_setup("DEMO")
        start = datetime(2026, 7, 21, 9, 0, tzinfo=UTC3)
        demo_baslat(self.conn, simdi=start)

        demo_durumunu_getir(
            self.conn,
            simdi=start + timedelta(days=5),
        )
        rollback = demo_durumunu_getir(
            self.conn,
            simdi=start + timedelta(days=2),
        )

        self.assertFalse(rollback["erisim_izni"])
        self.assertEqual(
            rollback["neden_kodu"],
            "SISTEM_SAATI_GERI_ALINDI",
        )

    def test_license_decision_routes_demo_without_key(self):
        self.complete_setup("DEMO")
        start = datetime(2026, 7, 21, 9, 0, tzinfo=UTC3)
        demo_baslat(self.conn, simdi=start)

        result = lisans_erisim_karari(
            self.conn,
            {},
            DEVICE_HASH,
            simdi=start + timedelta(days=1),
        )

        self.assertTrue(result["erisim_izni"])
        self.assertEqual(result["durum"], "DEMO_AKTIF")
        self.assertEqual(result["akis"], "NORMAL_GIRIS")


if __name__ == "__main__":
    unittest.main()

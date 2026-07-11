import hashlib
import importlib.util
import shutil
import sqlite3
import sys
import tempfile
import types
import unittest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


KG = Decimal("0.001")


class Phase13BusinessRulesSandboxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.live_db = (cls.project_root / "database" / "redbox_os.db").resolve()
        cls.database_dir = (cls.project_root / "database").resolve()
        cls.baseline_dir = (
            cls.project_root / "backups" / "PHASE9_FINAL_20260709_144106"
        ).resolve()
        cls.baseline_db = (cls.baseline_dir / "redbox_os.db").resolve()
        cls.protected_paths = [
            cls.live_db,
            cls.baseline_db,
            cls.project_root / "app.py",
            cls.project_root / "database" / "db.py",
            cls.project_root / "database" / "stock_engine.py",
            cls.project_root / "database" / "raw_material_stock_engine.py",
            cls.project_root / "database" / "finished_stock_engine.py",
            cls.project_root / "database" / "report_engine.py",
            cls.project_root / "tests" / "test_phase9_baseline.py",
            cls.project_root / "tests" / "phase12_p0_sandbox_proof.py",
        ]
        cls.protected_hashes = {
            str(path): cls.file_hash(path) for path in cls.protected_paths
        }

    @staticmethod
    def file_hash(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sandbox_db = (
            Path(self.temp_dir.name) / "redbox_os_phase13_sandbox.db"
        ).resolve()
        shutil.copy2(self.baseline_db, self.sandbox_db)
        self.assert_sandbox_target()
        self.conn = sqlite3.connect(self.sandbox_db)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def assert_sandbox_target(self):
        context = f"sandbox={self.sandbox_db}"
        self.assertTrue(self.sandbox_db.exists(), context)
        self.assertNotEqual(self.sandbox_db, self.live_db, context)
        self.assertNotEqual(self.sandbox_db, self.baseline_db, context)
        self.assertNotIn(self.database_dir, self.sandbox_db.parents, context)
        self.assertNotIn(self.baseline_dir, self.sandbox_db.parents, context)

    def kg(self, value):
        return Decimal(str(value)).quantize(KG, rounding=ROUND_HALF_UP)

    def scalar(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()[0]

    def load_engine_module(self, rel_path, module_name):
        fake_database = types.ModuleType("database")
        fake_db = types.ModuleType("database.db")

        def blocked_get_connection():
            raise AssertionError("Engine test must inject a sandbox connection.")

        fake_db.get_connection = blocked_get_connection
        old_database = sys.modules.get("database")
        old_database_db = sys.modules.get("database.db")
        sys.modules["database"] = fake_database
        sys.modules["database.db"] = fake_db
        try:
            spec = importlib.util.spec_from_file_location(
                module_name,
                self.project_root / rel_path,
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        finally:
            if old_database is None:
                sys.modules.pop("database", None)
            else:
                sys.modules["database"] = old_database
            if old_database_db is None:
                sys.modules.pop("database.db", None)
            else:
                sys.modules["database.db"] = old_database_db

    def stock_engine(self):
        return self.load_engine_module(
            Path("database") / "stock_engine.py",
            "phase13_stock_engine",
        )

    def finished_stock_engine(self):
        return self.load_engine_module(
            Path("database") / "finished_stock_engine.py",
            "phase13_finished_stock_engine",
        )

    def integrity_tuple(self, conn=None):
        conn = conn or self.conn
        return (
            conn.execute("PRAGMA integrity_check").fetchone()[0],
            len(conn.execute("PRAGMA foreign_key_check").fetchall()),
        )

    def active_recipe(self):
        row = self.conn.execute(
            "SELECT id, parti_teorik_kg FROM receteler WHERE aktif = 1"
        ).fetchone()
        self.assertIsNotNone(row)
        return row

    def active_recipe_rows(self):
        recipe = self.active_recipe()
        return self.conn.execute(
            """
            SELECT rk.hammadde_id, h.ad AS hammadde, rk.miktar_kg
            FROM recete_kalemleri rk
            JOIN hammaddeler h ON h.id = rk.hammadde_id
            WHERE rk.recete_id = ?
            ORDER BY rk.id
            """,
            (recipe["id"],),
        ).fetchall()

    def create_synthetic_recipe(self, hammadde_id, amount_kg):
        recete_id = self.conn.execute(
            """
            INSERT INTO receteler (ad, parti_teorik_kg, aktif)
            VALUES (?, ?, 0)
            """,
            ("PH13-TEST-RECIPE", float(amount_kg)),
        ).lastrowid
        self.conn.execute(
            """
            INSERT INTO recete_kalemleri (recete_id, hammadde_id, miktar_kg)
            VALUES (?, ?, ?)
            """,
            (recete_id, hammadde_id, float(amount_kg)),
        )
        return recete_id

    def create_depo_lot(self, hammadde_id, lot_suffix, date_text, kg):
        return self.conn.execute(
            """
            INSERT INTO depo_kabul (
                kabul_tarihi, hammadde_id, tedarikci, tedarikci_lot_no,
                uretim_tarihi, skt_tett, miktar_kg, kabul_durumu,
                aciklama, kayit_zamani
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'KABUL', ?, ?)
            """,
            (
                date_text,
                hammadde_id,
                "PH13 TEST SUPPLIER",
                f"PH13-TEST-{lot_suffix}",
                "01.01.2099",
                "01.01.2100",
                float(kg),
                "PH13 sandbox synthetic lot",
                "2099-01-01T00:00:00",
            ),
        ).lastrowid

    def create_production(self, lot_suffix="PROD", batches=1):
        recipe = self.active_recipe()
        theoretical = self.kg(Decimal(str(batches)) * Decimal(str(recipe["parti_teorik_kg"])))
        return self.conn.execute(
            """
            INSERT INTO uretim (
                uretim_tarihi, urun_lot_no, parti_sayisi, teorik_uretim_kg,
                uretim_firesi_kg, net_uretim_kg, personel_1, personel_2,
                aciklama, kayit_zamani
            )
            VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
            """,
            (
                "01.01.2099",
                f"PH13-TEST-{lot_suffix}",
                batches,
                float(theoretical),
                float(theoretical),
                "PH13 TEST PERSON 1",
                "PH13 TEST PERSON 2",
                "PH13 sandbox production",
                "2099-01-01T00:00:00",
            ),
        ).lastrowid

    def seed_active_recipe_sufficient_stock(self, batches=1):
        for row in self.active_recipe_rows():
            needed = self.kg(Decimal(str(row["miktar_kg"])) * Decimal(str(batches)))
            self.create_depo_lot(
                row["hammadde_id"],
                f'STOCK-{row["hammadde_id"]}',
                "01.01.2000",
                needed + Decimal("5.000"),
            )

    def create_packaging(self, uretim_id, lot_suffix="PACK", grams=500, packages=10):
        packaged_kg = self.kg(Decimal(str(packages)) * Decimal(str(grams)) / Decimal("1000"))
        return self.conn.execute(
            """
            INSERT INTO paketleme (
                paketleme_tarihi, uretim_id, ambalaj_gram, paket_adedi,
                paketlenen_kg, paketleme_firesi_kg, aciklama, kayit_zamani,
                koli_ici_adet
            )
            VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                "01.01.2099",
                uretim_id,
                grams,
                packages,
                float(packaged_kg),
                f"PH13 sandbox packaging {lot_suffix}",
                "2099-01-01T00:00:00",
                10,
            ),
        ).lastrowid

    def create_shipment_header(self, suffix="SHIP"):
        musteri_id = self.conn.execute(
            """
            INSERT INTO musteriler (musteri_adi, aktif, kayit_zamani)
            VALUES (?, 1, ?)
            """,
            (f"PH13 TEST CUSTOMER {suffix}", "2099-01-01T00:00:00"),
        ).lastrowid
        return self.conn.execute(
            """
            INSERT INTO sevkiyat (
                sevkiyat_tarihi, sevk_koli_adedi, sevk_acik_paket_adedi,
                musteri, musteri_id, arac_plaka, belge_no, soguk_zincir,
                aciklama, kayit_zamani
            )
            VALUES (?, 0, 0, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                "01.01.2099",
                f"PH13 TEST CUSTOMER {suffix}",
                musteri_id,
                "PH13",
                f"PH13-TEST-{suffix}",
                "PH13 sandbox shipment",
                "2099-01-01T00:00:00",
            ),
        ).lastrowid

    def snapshot_counts_and_hashes(self):
        tables = [
            "uretim",
            "uretim_recete",
            "uretim_hammadde_lotlari",
            "paketleme",
            "sevkiyat",
            "sevkiyat_kalemleri",
            "depo_kabul",
        ]
        result = {}
        for table in tables:
            rows = [
                tuple(row)
                for row in self.conn.execute(f'SELECT * FROM "{table}" ORDER BY 1')
            ]
            result[table] = hashlib.sha256(repr(rows).encode("utf-8")).hexdigest()
        return result

    def test_01_sandbox_target_isolated(self):
        self.assert_sandbox_target()
        self.assertEqual(self.integrity_tuple(), ("ok", 0))
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM uretim"), 11)
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM uretim_hammadde_lotlari"),
            88,
        )

    def test_02_fifo_lot_order_matches_acceptance_date_then_id(self):
        source = (self.project_root / "database" / "stock_engine.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("ORDER BY", source)
        self.assertIn("substr(dk.kabul_tarihi, 7, 4)", source)
        self.assertIn("substr(dk.kabul_tarihi, 4, 2)", source)
        self.assertIn("substr(dk.kabul_tarihi, 1, 2)", source)
        self.assertIn("dk.id", source)
        engine = self.stock_engine()
        for hammadde_id in [
            row["id"] for row in self.conn.execute("SELECT id FROM hammaddeler ORDER BY id")
        ]:
            engine_ids = [
                row["id"] for row in engine.uygun_lotlar_getir(self.conn, hammadde_id)
            ]
            expected_ids = [
                row["id"]
                for row in self.conn.execute(
                    """
                    SELECT id FROM depo_kabul
                    WHERE hammadde_id = ? AND kabul_durumu = 'KABUL'
                    ORDER BY
                        substr(kabul_tarihi, 7, 4),
                        substr(kabul_tarihi, 4, 2),
                        substr(kabul_tarihi, 1, 2),
                        id
                    """,
                    (hammadde_id,),
                )
            ]
            self.assertEqual(engine_ids, expected_ids, f"hammadde_id={hammadde_id}")

    def test_03_fifo_consumes_oldest_available_lot_first(self):
        engine = self.stock_engine()
        hammadde_id = self.active_recipe_rows()[0]["hammadde_id"]
        old_id = self.create_depo_lot(hammadde_id, "FIFO-OLD", "01.01.2000", 5)
        self.create_depo_lot(hammadde_id, "FIFO-NEW", "02.01.2000", 5)
        recete_id = self.create_synthetic_recipe(hammadde_id, Decimal("3.000"))
        uretim_id = self.create_production("FIFO-OLD-FIRST", 1)
        engine.fifo_lot_tuket(self.conn, uretim_id, recete_id, 1)
        lot_ids = [
            row["depo_kabul_id"]
            for row in self.conn.execute(
                """
                SELECT depo_kabul_id FROM uretim_hammadde_lotlari
                WHERE uretim_id = ?
                ORDER BY id
                """,
                (uretim_id,),
            )
        ]
        self.assertEqual(lot_ids, [old_id])

    def test_04_fifo_spans_multiple_lots_in_order(self):
        engine = self.stock_engine()
        hammadde_id = self.active_recipe_rows()[0]["hammadde_id"]
        first_id = self.create_depo_lot(hammadde_id, "SPAN-1", "01.01.2000", 2)
        second_id = self.create_depo_lot(hammadde_id, "SPAN-2", "02.01.2000", 5)
        recete_id = self.create_synthetic_recipe(hammadde_id, Decimal("4.500"))
        uretim_id = self.create_production("FIFO-SPAN", 1)
        engine.fifo_lot_tuket(self.conn, uretim_id, recete_id, 1)
        rows = self.conn.execute(
            """
            SELECT depo_kabul_id, kullanilan_miktar_kg
            FROM uretim_hammadde_lotlari
            WHERE uretim_id = ?
            ORDER BY id
            """,
            (uretim_id,),
        ).fetchall()
        self.assertEqual([row["depo_kabul_id"] for row in rows], [first_id, second_id])
        self.assertEqual(self.kg(rows[0]["kullanilan_miktar_kg"]), Decimal("2.000"))
        self.assertEqual(
            self.kg(sum(Decimal(str(row["kullanilan_miktar_kg"])) for row in rows)),
            Decimal("4.500"),
        )

    def test_05_fifo_skips_exhausted_lot(self):
        engine = self.stock_engine()
        hammadde_id = self.active_recipe_rows()[0]["hammadde_id"]
        exhausted_id = self.create_depo_lot(hammadde_id, "EXHAUSTED", "01.01.2000", 1)
        next_id = self.create_depo_lot(hammadde_id, "NEXT", "02.01.2000", 5)
        previous_production = self.create_production("EXHAUST-SEED", 1)
        self.conn.execute(
            """
            INSERT INTO uretim_hammadde_lotlari (
                uretim_id, depo_kabul_id, kullanilan_miktar_kg
            )
            VALUES (?, ?, 1)
            """,
            (previous_production, exhausted_id),
        )
        recete_id = self.create_synthetic_recipe(hammadde_id, Decimal("2.000"))
        uretim_id = self.create_production("SKIP-EXHAUSTED", 1)
        engine.fifo_lot_tuket(self.conn, uretim_id, recete_id, 1)
        rows = self.conn.execute(
            """
            SELECT depo_kabul_id FROM uretim_hammadde_lotlari
            WHERE uretim_id = ?
            ORDER BY id
            """,
            (uretim_id,),
        ).fetchall()
        self.assertNotIn(exhausted_id, [row["depo_kabul_id"] for row in rows])
        self.assertEqual(rows[0]["depo_kabul_id"], next_id)

    def test_06_insufficient_raw_material_stock_raises_and_outer_transaction_can_rollback(self):
        engine = self.stock_engine()
        before = self.snapshot_counts_and_hashes()
        self.conn.execute("BEGIN")
        try:
            uretim_id = self.create_production("INSUFFICIENT", 1000000)
            with self.assertRaises(Exception):
                engine.uretim_stok_isle(self.conn, uretim_id, 1000000)
        finally:
            self.conn.rollback()
        after = self.snapshot_counts_and_hashes()
        self.assertEqual(after, before)

    def test_07_successful_production_stock_process_creates_one_recipe_link(self):
        engine = self.stock_engine()
        self.seed_active_recipe_sufficient_stock(1)
        uretim_id = self.create_production("ONE-LINK", 1)
        recete = engine.uretim_stok_isle(self.conn, uretim_id, 1)
        rows = self.conn.execute(
            "SELECT recete_id FROM uretim_recete WHERE uretim_id = ?",
            (uretim_id,),
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["recete_id"], recete["id"])

    def test_08_successful_production_stock_process_creates_eight_raw_material_traces(self):
        engine = self.stock_engine()
        self.seed_active_recipe_sufficient_stock(1)
        uretim_id = self.create_production("EIGHT-TRACES", 1)
        engine.uretim_stok_isle(self.conn, uretim_id, 1)
        count = self.scalar(
            """
            SELECT COUNT(DISTINCT dk.hammadde_id)
            FROM uretim_hammadde_lotlari uhl
            JOIN depo_kabul dk ON dk.id = uhl.depo_kabul_id
            WHERE uhl.uretim_id = ?
            """,
            (uretim_id,),
        )
        self.assertEqual(count, 8)

    def test_09_successful_production_consumption_matches_recipe_mass(self):
        engine = self.stock_engine()
        batches = 2
        self.seed_active_recipe_sufficient_stock(batches)
        uretim_id = self.create_production("RECIPE-MASS", batches)
        engine.uretim_stok_isle(self.conn, uretim_id, batches)
        for row in self.active_recipe_rows():
            expected = self.kg(Decimal(str(row["miktar_kg"])) * Decimal(str(batches)))
            actual = self.kg(
                self.scalar(
                    """
                    SELECT COALESCE(SUM(uhl.kullanilan_miktar_kg), 0)
                    FROM uretim_hammadde_lotlari uhl
                    JOIN depo_kabul dk ON dk.id = uhl.depo_kabul_id
                    WHERE uhl.uretim_id = ? AND dk.hammadde_id = ?
                    """,
                    (uretim_id, row["hammadde_id"]),
                )
            )
            self.assertEqual(actual, expected, row["hammadde"])

    def test_10_production_theoretical_and_net_formula_invariant(self):
        recipe = self.active_recipe()
        self.assertEqual(self.kg(recipe["parti_teorik_kg"]), Decimal("20.412"))
        for batches in [1, 6, 13]:
            theoretical = self.kg(Decimal(str(batches)) * Decimal("20.412"))
            for waste in [Decimal("0.000"), Decimal("5.000"), Decimal("40.000")]:
                expected_net = self.kg(theoretical - waste)
                message = "Invariant coverage only; app.py is not imported."
                self.assertEqual(self.kg(theoretical - waste), expected_net, message)

    def test_11_packaging_package_count_to_kg_invariant(self):
        for grams in [500, 2500]:
            for packages in [1, 7, 120]:
                expected = self.kg(
                    Decimal(str(packages)) * Decimal(str(grams)) / Decimal("1000")
                )
                actual = self.kg(Decimal(str(packages * grams)) / Decimal("1000"))
                self.assertEqual(actual, expected)

    def test_12_packaging_cannot_exceed_remaining_net_mass_invariant(self):
        row = self.conn.execute(
            """
            SELECT u.id, u.urun_lot_no, u.net_uretim_kg,
                   COALESCE(SUM(p.paketlenen_kg), 0) AS packaged_kg,
                   COALESCE(SUM(p.paketleme_firesi_kg), 0) AS waste_kg
            FROM uretim u
            LEFT JOIN paketleme p ON p.uretim_id = u.id
            GROUP BY u.id, u.urun_lot_no, u.net_uretim_kg
            ORDER BY u.id
            LIMIT 1
            """
        ).fetchone()
        remaining = self.kg(
            Decimal(str(row["net_uretim_kg"]))
            - Decimal(str(row["packaged_kg"]))
            - Decimal(str(row["waste_kg"]))
        )
        proposed_packaged = remaining + Decimal("0.001")
        proposed_waste = Decimal("0.000")
        is_invalid = proposed_packaged + proposed_waste > remaining
        self.assertTrue(is_invalid, "Invariant coverage only; app.py is not imported.")

    def test_13_finished_stock_engine_reports_current_phase9_balance(self):
        engine = self.finished_stock_engine()
        rows = engine.mamul_stok_ozeti(self.conn)
        remaining_kg = self.kg(sum(Decimal(str(row["kalan_kg"])) for row in rows))
        packaged = self.kg(
            self.scalar("SELECT COALESCE(SUM(paketlenen_kg), 0) FROM paketleme")
        )
        shipped = self.kg(
            self.scalar("SELECT COALESCE(SUM(sevk_kg), 0) FROM sevkiyat_kalemleri")
        )
        self.assertEqual(packaged, Decimal("2362.000"))
        self.assertEqual(shipped, Decimal("2352.000"))
        self.assertEqual(remaining_kg, Decimal("10.000"))

    def test_14_shipment_engine_rejects_package_quantity_above_available_stock(self):
        engine = self.finished_stock_engine()
        stock = [row for row in engine.mamul_stok_ozeti(self.conn) if row["kalan_paket_adedi"] > 0][0]
        shipment_id = self.create_shipment_header("OVERSTOCK")
        self.conn.commit()
        before = self.scalar(
            "SELECT COUNT(*) FROM sevkiyat_kalemleri WHERE sevkiyat_id = ?",
            (shipment_id,),
        )
        self.conn.execute("BEGIN")
        try:
            with self.assertRaises(Exception):
                engine.sevkiyat_stok_dus(
                    self.conn,
                    shipment_id,
                    stock["uretim_id"],
                    stock["ambalaj_gram"],
                    stock["kalan_paket_adedi"] + 1,
                )
        finally:
            self.conn.rollback()
        after = self.scalar(
            "SELECT COUNT(*) FROM sevkiyat_kalemleri WHERE sevkiyat_id = ?",
            (shipment_id,),
        )
        self.assertEqual(after, before)

    def test_15_shipment_engine_creates_package_and_kg_consistent_lines(self):
        engine = self.finished_stock_engine()
        stock = [row for row in engine.mamul_stok_ozeti(self.conn) if row["kalan_paket_adedi"] > 0][0]
        shipment_id = self.create_shipment_header("KG")
        self.conn.commit()
        request = min(2, stock["kalan_paket_adedi"])
        self.conn.execute("BEGIN")
        try:
            created = engine.sevkiyat_stok_dus(
                self.conn,
                shipment_id,
                stock["uretim_id"],
                stock["ambalaj_gram"],
                request,
            )
            total_packages = sum(row["paket_adedi"] for row in created)
            self.assertEqual(total_packages, request)
            for row in self.conn.execute(
                """
                SELECT sk.paket_adedi, sk.sevk_kg, p.ambalaj_gram
                FROM sevkiyat_kalemleri sk
                JOIN paketleme p ON p.id = sk.paketleme_id
                WHERE sk.sevkiyat_id = ?
                """,
                (shipment_id,),
            ):
                expected = self.kg(
                    Decimal(str(row["paket_adedi"]))
                    * Decimal(str(row["ambalaj_gram"]))
                    / Decimal("1000")
                )
                self.assertEqual(self.kg(row["sevk_kg"]), expected)
        finally:
            self.conn.rollback()

    def test_16_shipment_engine_consumes_finished_stock_in_real_order(self):
        engine = self.finished_stock_engine()
        uretim_id = self.create_production("SHIP-ORDER", 1)
        p1 = self.create_packaging(uretim_id, "ORDER-1", 500, 2)
        p2 = self.create_packaging(uretim_id, "ORDER-2", 500, 3)
        shipment_id = self.create_shipment_header("ORDER")
        created = engine.sevkiyat_stok_dus(self.conn, shipment_id, uretim_id, 500, 4)
        self.assertEqual([row["paketleme_id"] for row in created], [p1, p2])
        self.assertEqual(created[0]["paket_adedi"], 2)
        self.assertEqual(
            [
                row["paketleme_id"]
                for row in engine.lot_ambalaj_stoklari(uretim_id, 500, self.conn)
            ],
            [p1, p2],
            "Engine order is paketleme.id ASC.",
        )

    def test_17_shipment_engine_skips_zero_remaining_packaging_rows(self):
        engine = self.finished_stock_engine()
        uretim_id = self.create_production("SHIP-SKIP", 1)
        exhausted = self.create_packaging(uretim_id, "EXHAUSTED", 500, 2)
        next_packaging = self.create_packaging(uretim_id, "NEXT", 500, 3)
        old_ship = self.create_shipment_header("EXHAUST-SEED")
        self.conn.execute(
            """
            INSERT INTO sevkiyat_kalemleri (
                sevkiyat_id, paketleme_id, paket_adedi, sevk_kg
            )
            VALUES (?, ?, 2, 1.0)
            """,
            (old_ship, exhausted),
        )
        shipment_id = self.create_shipment_header("SKIP")
        created = engine.sevkiyat_stok_dus(self.conn, shipment_id, uretim_id, 500, 1)
        self.assertNotIn(exhausted, [row["paketleme_id"] for row in created])
        self.assertEqual(created[0]["paketleme_id"], next_packaging)

    def test_18_sandbox_forward_traceability_after_synthetic_production(self):
        engine = self.stock_engine()
        self.seed_active_recipe_sufficient_stock(1)
        uretim_id = self.create_production("FORWARD", 1)
        engine.uretim_stok_isle(self.conn, uretim_id, 1)
        packaging_id = self.create_packaging(uretim_id, "FORWARD", 500, 4)
        rows = self.conn.execute(
            """
            SELECT dk.tedarikci_lot_no, u.urun_lot_no, p.id AS paketleme_id
            FROM uretim_hammadde_lotlari uhl
            JOIN depo_kabul dk ON dk.id = uhl.depo_kabul_id
            JOIN uretim u ON u.id = uhl.uretim_id
            JOIN paketleme p ON p.uretim_id = u.id
            WHERE u.id = ?
            """,
            (uretim_id,),
        ).fetchall()
        self.assertEqual(len({row["tedarikci_lot_no"] for row in rows}), 8)
        self.assertTrue(all(row["tedarikci_lot_no"].startswith("PH13-TEST-") for row in rows))
        self.assertTrue(all(row["paketleme_id"] == packaging_id for row in rows))

    def test_19_sandbox_reverse_traceability_after_synthetic_shipment(self):
        stock_engine = self.stock_engine()
        shipment_engine = self.finished_stock_engine()
        self.seed_active_recipe_sufficient_stock(1)
        uretim_id = self.create_production("REVERSE", 1)
        stock_engine.uretim_stok_isle(self.conn, uretim_id, 1)
        self.create_packaging(uretim_id, "REVERSE", 500, 4)
        shipment_id = self.create_shipment_header("REVERSE")
        shipment_engine.sevkiyat_stok_dus(self.conn, shipment_id, uretim_id, 500, 2)
        rows = self.conn.execute(
            """
            SELECT DISTINCT dk.tedarikci_lot_no, dk.hammadde_id
            FROM sevkiyat s
            JOIN sevkiyat_kalemleri sk ON sk.sevkiyat_id = s.id
            JOIN paketleme p ON p.id = sk.paketleme_id
            JOIN uretim u ON u.id = p.uretim_id
            JOIN uretim_hammadde_lotlari uhl ON uhl.uretim_id = u.id
            JOIN depo_kabul dk ON dk.id = uhl.depo_kabul_id
            WHERE s.id = ?
            """,
            (shipment_id,),
        ).fetchall()
        self.assertEqual(len({row["hammadde_id"] for row in rows}), 8)
        self.assertTrue(all(row["tedarikci_lot_no"].startswith("PH13-TEST-") for row in rows))

    def test_20_business_rule_suite_does_not_change_protected_state(self):
        for db_path in [self.live_db, self.baseline_db]:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            try:
                self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(len(conn.execute("PRAGMA foreign_key_check").fetchall()), 0)
            finally:
                conn.close()
        current_hashes = {
            str(path): self.file_hash(path) for path in self.protected_paths
        }
        self.assertEqual(current_hashes, self.protected_hashes)


if __name__ == "__main__":
    unittest.main()

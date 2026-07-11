import sqlite3
import unittest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


KG = Decimal("0.001")


class Phase9BaselineRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.db_path = (cls.project_root / "database" / "redbox_os.db").resolve()
        cls.db_uri = f"file:{cls.db_path}?mode=ro"

    def setUp(self):
        self.conn = sqlite3.connect(self.db_uri, uri=True)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA query_only = ON")
        query_only = self.conn.execute("PRAGMA query_only").fetchone()[0]
        self.assertEqual(query_only, 1, "SQLite connection is not query-only.")

    def tearDown(self):
        self.conn.close()

    def kg(self, value):
        return Decimal(str(value)).quantize(KG, rounding=ROUND_HALF_UP)

    def scalar(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()[0]

    def active_recipe(self):
        rows = self.conn.execute(
            """
            SELECT id, ad, parti_teorik_kg
            FROM receteler
            WHERE aktif = 1
            ORDER BY id
            """
        ).fetchall()
        self.assertEqual(
            len(rows),
            1,
            f"Expected exactly one active recipe, found {len(rows)}.",
        )
        return rows[0]

    def active_recipe_rows(self):
        recipe = self.active_recipe()
        return self.conn.execute(
            """
            SELECT
                rk.hammadde_id,
                h.ad AS hammadde,
                rk.miktar_kg
            FROM recete_kalemleri rk
            JOIN hammaddeler h
              ON h.id = rk.hammadde_id
            WHERE rk.recete_id = ?
            ORDER BY rk.id
            """,
            (recipe["id"],),
        ).fetchall()

    def test_01_database_integrity(self):
        result = self.scalar("PRAGMA integrity_check")
        self.assertEqual(result, "ok")

    def test_02_foreign_key_integrity(self):
        rows = self.conn.execute("PRAGMA foreign_key_check").fetchall()
        self.assertEqual(rows, [], f"Foreign key violations found: {rows}")

    def test_03_protected_table_counts(self):
        expected = {
            "uretim": 11,
            "uretim_recete": 11,
            "uretim_hammadde_lotlari": 88,
            "paketleme": 13,
            "sevkiyat": 8,
            "sevkiyat_kalemleri": 16,
        }

        for table, expected_count in expected.items():
            actual = self.scalar(f'SELECT COUNT(*) FROM "{table}"')
            self.assertEqual(
                actual,
                expected_count,
                f"{table}: expected {expected_count}, actual {actual}",
            )

    def test_04_active_recipe_contract(self):
        recipe = self.active_recipe()
        self.assertEqual(self.kg(recipe["parti_teorik_kg"]), Decimal("20.412"))

    def test_05_active_recipe_raw_material_contract(self):
        expected = {
            "Patates Unu": Decimal("5.200"),
            "Nişasta": Decimal("2.560"),
            "Mısır Unu": Decimal("1.280"),
            "Metilselüloz Benecel A4M E461": Decimal("0.120"),
            "Tavuk Çeşnisi": Decimal("0.320"),
            "Sarımsak Tozu": Decimal("0.064"),
            "Karabiber": Decimal("0.024"),
            "Tuz": Decimal("0.144"),
        }
        rows = self.active_recipe_rows()
        actual = {row["hammadde"]: self.kg(row["miktar_kg"]) for row in rows}

        self.assertEqual(len(rows), 8)
        self.assertEqual(set(actual), set(expected))

        for name, expected_kg in expected.items():
            self.assertEqual(
                actual[name],
                expected_kg,
                f"{name}: expected {expected_kg}, actual {actual[name]}",
            )

    def test_06_benecel_accepted_lot(self):
        rows = self.conn.execute(
            """
            SELECT DISTINCT dk.tedarikci_lot_no
            FROM uretim_hammadde_lotlari uhl
            JOIN depo_kabul dk
              ON dk.id = uhl.depo_kabul_id
            JOIN hammaddeler h
              ON h.id = dk.hammadde_id
            WHERE h.ad = ?
            ORDER BY dk.tedarikci_lot_no
            """,
            ("Metilselüloz Benecel A4M E461",),
        ).fetchall()
        lots = [row["tedarikci_lot_no"] for row in rows]
        self.assertEqual(
            lots,
            ["2743063"],
            f"Traced Benecel lot values: {lots}",
        )

    def test_07_production_recipe_link_uniqueness(self):
        rows = self.conn.execute(
            """
            SELECT
                u.id,
                u.urun_lot_no,
                COUNT(ur.id) AS link_count
            FROM uretim u
            LEFT JOIN uretim_recete ur
              ON ur.uretim_id = u.id
            GROUP BY u.id, u.urun_lot_no
            ORDER BY u.id
            """
        ).fetchall()

        self.assertEqual(len(rows), 11)
        for row in rows:
            self.assertEqual(
                row["link_count"],
                1,
                (
                    f'Production {row["id"]} / {row["urun_lot_no"]}: '
                    f'expected 1 recipe link, actual {row["link_count"]}'
                ),
            )

    def test_08_production_theoretical_mass(self):
        rows = self.conn.execute(
            """
            SELECT
                u.id,
                u.urun_lot_no,
                u.parti_sayisi,
                u.teorik_uretim_kg,
                r.parti_teorik_kg
            FROM uretim u
            JOIN uretim_recete ur
              ON ur.uretim_id = u.id
            JOIN receteler r
              ON r.id = ur.recete_id
            ORDER BY u.id
            """
        ).fetchall()

        for row in rows:
            calculated = self.kg(
                Decimal(str(row["parti_sayisi"]))
                * Decimal(str(row["parti_teorik_kg"]))
            )
            stored = self.kg(row["teorik_uretim_kg"])
            diff = self.kg(stored - calculated)
            self.assertEqual(
                diff,
                Decimal("0.000"),
                (
                    f'Production {row["id"]} / {row["urun_lot_no"]}: '
                    f'batches {row["parti_sayisi"]}, calculated {calculated}, '
                    f"stored {stored}, difference {diff}"
                ),
            )

    def test_09_production_net_mass(self):
        rows = self.conn.execute(
            """
            SELECT
                id,
                urun_lot_no,
                teorik_uretim_kg,
                uretim_firesi_kg,
                net_uretim_kg
            FROM uretim
            ORDER BY id
            """
        ).fetchall()

        for row in rows:
            expected = self.kg(
                Decimal(str(row["teorik_uretim_kg"]))
                - Decimal(str(row["uretim_firesi_kg"]))
            )
            stored = self.kg(row["net_uretim_kg"])
            diff = self.kg(stored - expected)
            self.assertEqual(
                diff,
                Decimal("0.000"),
                (
                    f'Production {row["id"]} / {row["urun_lot_no"]}: '
                    f'theoretical {self.kg(row["teorik_uretim_kg"])}, '
                    f'waste {self.kg(row["uretim_firesi_kg"])}, '
                    f"expected net {expected}, stored net {stored}, "
                    f"difference {diff}"
                ),
            )

    def test_10_eight_raw_materials_per_production(self):
        rows = self.conn.execute(
            """
            SELECT
                u.id,
                u.urun_lot_no,
                COUNT(DISTINCT dk.hammadde_id) AS raw_material_count
            FROM uretim u
            LEFT JOIN uretim_hammadde_lotlari uhl
              ON uhl.uretim_id = u.id
            LEFT JOIN depo_kabul dk
              ON dk.id = uhl.depo_kabul_id
            LEFT JOIN hammaddeler h
              ON h.id = dk.hammadde_id
            GROUP BY u.id, u.urun_lot_no
            ORDER BY u.id
            """
        ).fetchall()

        for row in rows:
            self.assertEqual(
                row["raw_material_count"],
                8,
                (
                    f'Production {row["id"]} / {row["urun_lot_no"]}: '
                    f'expected 8 traced raw materials, '
                    f'actual {row["raw_material_count"]}'
                ),
            )

    def test_11_recipe_consumption_mass_balance(self):
        recipe_rows = self.active_recipe_rows()
        recipe_by_material = {
            row["hammadde_id"]: (row["hammadde"], self.kg(row["miktar_kg"]))
            for row in recipe_rows
        }
        productions = self.conn.execute(
            """
            SELECT id, urun_lot_no, parti_sayisi
            FROM uretim
            ORDER BY id
            """
        ).fetchall()
        checks = 0

        for production in productions:
            actual_rows = self.conn.execute(
                """
                SELECT
                    dk.hammadde_id,
                    COALESCE(SUM(uhl.kullanilan_miktar_kg), 0) AS actual_kg
                FROM uretim_hammadde_lotlari uhl
                JOIN depo_kabul dk
                  ON dk.id = uhl.depo_kabul_id
                WHERE uhl.uretim_id = ?
                GROUP BY dk.hammadde_id
                """,
                (production["id"],),
            ).fetchall()
            actual_by_material = {
                row["hammadde_id"]: self.kg(row["actual_kg"])
                for row in actual_rows
            }

            for hammadde_id, (name, recipe_kg) in recipe_by_material.items():
                expected = self.kg(
                    recipe_kg * Decimal(str(production["parti_sayisi"]))
                )
                actual = actual_by_material.get(hammadde_id, Decimal("0.000"))
                diff = self.kg(actual - expected)
                checks += 1
                self.assertEqual(
                    diff,
                    Decimal("0.000"),
                    (
                        f'{production["urun_lot_no"]} / {name}: '
                        f"expected {expected}, actual {actual}, "
                        f"difference {diff}"
                    ),
                )

        self.assertEqual(checks, 88)

    def test_12_production_packaging_mass_balance(self):
        rows = self.conn.execute(
            """
            SELECT
                u.id,
                u.urun_lot_no,
                u.net_uretim_kg,
                COALESCE(SUM(p.paketlenen_kg), 0) AS packaged_kg,
                COALESCE(SUM(p.paketleme_firesi_kg), 0) AS waste_kg
            FROM uretim u
            LEFT JOIN paketleme p
              ON p.uretim_id = u.id
            GROUP BY u.id, u.urun_lot_no, u.net_uretim_kg
            ORDER BY u.id
            """
        ).fetchall()

        for row in rows:
            expected = self.kg(row["net_uretim_kg"])
            actual = self.kg(
                Decimal(str(row["packaged_kg"])) + Decimal(str(row["waste_kg"]))
            )
            self.assertEqual(
                actual,
                expected,
                f'{row["urun_lot_no"]}: net {expected}, packaged plus waste {actual}',
            )

    def test_13_package_count_to_kg_contract(self):
        rows = self.conn.execute(
            """
            SELECT
                p.id,
                u.urun_lot_no,
                p.paket_adedi,
                p.ambalaj_gram,
                p.paketlenen_kg
            FROM paketleme p
            JOIN uretim u
              ON u.id = p.uretim_id
            ORDER BY p.id
            """
        ).fetchall()

        for row in rows:
            expected = self.kg(
                Decimal(str(row["paket_adedi"]))
                * Decimal(str(row["ambalaj_gram"]))
                / Decimal("1000")
            )
            actual = self.kg(row["paketlenen_kg"])
            self.assertEqual(
                actual,
                expected,
                (
                    f'Packaging {row["id"]} / {row["urun_lot_no"]}: '
                    f"expected {expected}, actual {actual}"
                ),
            )

    def test_14_shipment_line_package_to_kg_contract(self):
        rows = self.conn.execute(
            """
            SELECT
                sk.id,
                sk.paket_adedi,
                sk.sevk_kg,
                p.ambalaj_gram
            FROM sevkiyat_kalemleri sk
            JOIN paketleme p
              ON p.id = sk.paketleme_id
            ORDER BY sk.id
            """
        ).fetchall()

        for row in rows:
            expected = self.kg(
                Decimal(str(row["paket_adedi"]))
                * Decimal(str(row["ambalaj_gram"]))
                / Decimal("1000")
            )
            actual = self.kg(row["sevk_kg"])
            self.assertEqual(
                actual,
                expected,
                f'Shipment line {row["id"]}: expected {expected}, actual {actual}',
            )

    def test_15_no_finished_product_negative_stock(self):
        rows = self.conn.execute(
            """
            SELECT
                p.id,
                p.paket_adedi,
                p.paketlenen_kg,
                COALESCE(SUM(sk.paket_adedi), 0) AS shipped_packages,
                COALESCE(SUM(sk.sevk_kg), 0) AS shipped_kg
            FROM paketleme p
            LEFT JOIN sevkiyat_kalemleri sk
              ON sk.paketleme_id = p.id
            GROUP BY p.id, p.paket_adedi, p.paketlenen_kg
            ORDER BY p.id
            """
        ).fetchall()

        for row in rows:
            remaining_packages = int(row["paket_adedi"]) - int(row["shipped_packages"])
            remaining_kg = self.kg(
                Decimal(str(row["paketlenen_kg"])) - Decimal(str(row["shipped_kg"]))
            )
            self.assertGreaterEqual(
                remaining_packages,
                0,
                f'Packaging {row["id"]}: negative package stock {remaining_packages}',
            )
            self.assertGreaterEqual(
                remaining_kg,
                Decimal("0.000"),
                f'Packaging {row["id"]}: negative kg stock {remaining_kg}',
            )

    def test_16_global_production_mass_balance(self):
        net = self.kg(self.scalar("SELECT COALESCE(SUM(net_uretim_kg), 0) FROM uretim"))
        packaged = self.kg(
            self.scalar("SELECT COALESCE(SUM(paketlenen_kg), 0) FROM paketleme")
        )
        waste = self.kg(
            self.scalar("SELECT COALESCE(SUM(paketleme_firesi_kg), 0) FROM paketleme")
        )
        diff = self.kg(net - packaged - waste)

        self.assertEqual(net, Decimal("2369.852"))
        self.assertEqual(packaged, Decimal("2362.000"))
        self.assertEqual(waste, Decimal("7.852"))
        self.assertEqual(diff, Decimal("0.000"))

    def test_17_global_finished_product_mass_balance(self):
        packaged = self.kg(
            self.scalar("SELECT COALESCE(SUM(paketlenen_kg), 0) FROM paketleme")
        )
        shipped = self.kg(
            self.scalar("SELECT COALESCE(SUM(sevk_kg), 0) FROM sevkiyat_kalemleri")
        )
        remaining = self.kg(packaged - shipped)
        diff = self.kg(packaged - shipped - remaining)

        self.assertEqual(packaged, Decimal("2362.000"))
        self.assertEqual(shipped, Decimal("2352.000"))
        self.assertEqual(remaining, Decimal("10.000"))
        self.assertEqual(diff, Decimal("0.000"))

    def test_18_forward_traceability_completeness(self):
        rows = self.conn.execute(
            """
            SELECT
                uhl.id AS trace_id,
                u.id AS production_id,
                u.urun_lot_no,
                dk.id AS warehouse_acceptance_id,
                dk.tedarikci_lot_no,
                h.id AS raw_material_id,
                h.ad AS raw_material_name,
                COUNT(p.id) AS packaging_count
            FROM uretim_hammadde_lotlari uhl
            JOIN uretim u
              ON u.id = uhl.uretim_id
            JOIN depo_kabul dk
              ON dk.id = uhl.depo_kabul_id
            JOIN hammaddeler h
              ON h.id = dk.hammadde_id
            LEFT JOIN paketleme p
              ON p.uretim_id = u.id
            GROUP BY
                uhl.id,
                u.id,
                u.urun_lot_no,
                dk.id,
                dk.tedarikci_lot_no,
                h.id,
                h.ad
            ORDER BY uhl.id
            """
        ).fetchall()

        self.assertEqual(len(rows), 88)
        for row in rows:
            required = [
                "production_id",
                "urun_lot_no",
                "warehouse_acceptance_id",
                "tedarikci_lot_no",
                "raw_material_id",
                "raw_material_name",
            ]
            for key in required:
                self.assertIsNotNone(row[key], f'Trace row {row["trace_id"]}: {key}')
            self.assertGreater(
                row["packaging_count"],
                0,
                f'Trace row {row["trace_id"]}: no packaging for protected production',
            )

    def test_19_reverse_traceability_completeness(self):
        rows = self.conn.execute(
            """
            SELECT
                sk.id AS shipment_line_id,
                s.id AS shipment_id,
                s.musteri,
                s.musteri_id,
                p.id AS packaging_id,
                u.id AS production_id,
                u.urun_lot_no,
                COUNT(DISTINCT dk.hammadde_id) AS raw_material_count
            FROM sevkiyat_kalemleri sk
            JOIN sevkiyat s
              ON s.id = sk.sevkiyat_id
            JOIN paketleme p
              ON p.id = sk.paketleme_id
            JOIN uretim u
              ON u.id = p.uretim_id
            JOIN uretim_hammadde_lotlari uhl
              ON uhl.uretim_id = u.id
            JOIN depo_kabul dk
              ON dk.id = uhl.depo_kabul_id
            GROUP BY
                sk.id,
                s.id,
                s.musteri,
                s.musteri_id,
                p.id,
                u.id,
                u.urun_lot_no
            ORDER BY sk.id
            """
        ).fetchall()

        self.assertEqual(len(rows), 16)
        for row in rows:
            self.assertIsNotNone(row["shipment_id"])
            self.assertTrue(row["musteri"] or row["musteri_id"])
            self.assertIsNotNone(row["packaging_id"])
            self.assertIsNotNone(row["production_id"])
            self.assertIsNotNone(row["urun_lot_no"])
            self.assertEqual(
                row["raw_material_count"],
                8,
                (
                    f'Shipment line {row["shipment_line_id"]}: '
                    f'expected 8 traced raw materials, '
                    f'actual {row["raw_material_count"]}'
                ),
            )

    def test_20_phase9_protected_summary_contract(self):
        production_count = self.scalar("SELECT COUNT(*) FROM uretim")
        trace_count = self.scalar("SELECT COUNT(*) FROM uretim_hammadde_lotlari")
        packaging_count = self.scalar("SELECT COUNT(*) FROM paketleme")
        shipment_count = self.scalar("SELECT COUNT(*) FROM sevkiyat")
        shipment_line_count = self.scalar("SELECT COUNT(*) FROM sevkiyat_kalemleri")
        net = self.kg(self.scalar("SELECT COALESCE(SUM(net_uretim_kg), 0) FROM uretim"))
        packaged = self.kg(
            self.scalar("SELECT COALESCE(SUM(paketlenen_kg), 0) FROM paketleme")
        )
        waste = self.kg(
            self.scalar("SELECT COALESCE(SUM(paketleme_firesi_kg), 0) FROM paketleme")
        )
        shipped = self.kg(
            self.scalar("SELECT COALESCE(SUM(sevk_kg), 0) FROM sevkiyat_kalemleri")
        )
        finished_stock = self.kg(packaged - shipped)
        production_diff = self.kg(
            self.scalar(
                """
                SELECT
                    COALESCE(SUM(teorik_uretim_kg), 0)
                    - COALESCE(SUM(uretim_firesi_kg), 0)
                    - COALESCE(SUM(net_uretim_kg), 0)
                FROM uretim
                """
            )
        )
        finished_diff = self.kg(packaged - shipped - finished_stock)

        self.assertEqual(production_count, 11)
        self.assertEqual(trace_count, 88)
        self.assertEqual(packaging_count, 13)
        self.assertEqual(shipment_count, 8)
        self.assertEqual(shipment_line_count, 16)
        self.assertEqual(net, Decimal("2369.852"))
        self.assertEqual(packaged, Decimal("2362.000"))
        self.assertEqual(waste, Decimal("7.852"))
        self.assertEqual(shipped, Decimal("2352.000"))
        self.assertEqual(finished_stock, Decimal("10.000"))
        self.assertEqual(production_diff, Decimal("0.000"))
        self.assertEqual(finished_diff, Decimal("0.000"))


if __name__ == "__main__":
    unittest.main()

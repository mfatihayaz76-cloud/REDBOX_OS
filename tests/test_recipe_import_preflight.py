import csv
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.recipe_import_engine import (
    ALL_HEADERS,
    CATALOG_SHEET_NAME,
    REQUIRED_HEADERS,
    katalog_dosyasi_on_kontrol,
    katalog_on_kontrol,
)


SCHEMA = """
CREATE TABLE hammaddeler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT NOT NULL UNIQUE,
    birim TEXT NOT NULL DEFAULT 'kg',
    aktif INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE urunler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    urun_kodu TEXT NOT NULL UNIQUE COLLATE NOCASE,
    urun_adi TEXT NOT NULL UNIQUE COLLATE NOCASE,
    kategori TEXT,
    barkod TEXT UNIQUE,
    birim TEXT NOT NULL DEFAULT 'KG',
    raf_omru_gun INTEGER,
    saklama_sicakligi TEXT,
    aktif INTEGER NOT NULL DEFAULT 1,
    aciklama TEXT,
    kayit_zamani TEXT NOT NULL
);

CREATE TABLE receteler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT NOT NULL UNIQUE,
    parti_teorik_kg REAL NOT NULL,
    aktif INTEGER NOT NULL DEFAULT 1,
    revizyon_no TEXT,
    gecerlilik_tarihi TEXT,
    revizyon_aciklamasi TEXT,
    olusturan_personel_id INTEGER,
    urun_id INTEGER,
    recete_kodu TEXT,
    proses_suyu_kg REAL NOT NULL DEFAULT 0,
    durum TEXT NOT NULL DEFAULT 'TASLAK'
);
"""


class RecipeImportPreflightTest(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.executemany(
            """
            INSERT INTO hammaddeler (
                id,
                ad,
                birim,
                aktif
            )
            VALUES (?, ?, 'kg', ?)
            """,
            (
                (1, "Patates Unu", 1),
                (2, "Nişasta", 1),
                (3, "Pasif Hammadde", 0),
            ),
        )

    def tearDown(self):
        self.conn.close()

    def valid_row(self, number=1, **changes):
        row = {
            "_satir": number + 1,
            "urun_kodu": f"TEST{number:03d}",
            "urun_adi": f"Test Ürünü {number:03d}",
            "kategori": "Test",
            "barkod": "",
            "birim": "KG",
            "raf_omru_gun": "365",
            "saklama_sicakligi": "-18°C",
            "urun_aciklama": "CRC-2 sandbox",
            "recete_kodu": f"TEST{number:03d}-REC",
            "recete_adi": (
                f"TEST ÜRÜNÜ {number:03d} ANA REÇETE"
            ),
            "revizyon_no": "00",
            "gecerlilik_tarihi": "19.07.2026",
            "durum": "AKTIF",
            "parti_teorik_kg": "1.000",
            "proses_suyu_kg": "0",
            "revizyon_aciklamasi": "İlk kontrollü sürüm",
            "hammadde_adi": "Patates Unu",
            "miktar_kg": "1.000",
        }
        row.update(changes)
        return row

    def error_codes(self, report):
        return {
            error["kod"]
            for error in report["hatalar"]
        }

    def test_61_product_catalog_dry_run(self):
        rows = [
            self.valid_row(number)
            for number in range(1, 62)
        ]

        before = {
            "urunler": self.conn.execute(
                "SELECT COUNT(*) FROM urunler"
            ).fetchone()[0],
            "receteler": self.conn.execute(
                "SELECT COUNT(*) FROM receteler"
            ).fetchone()[0],
        }

        report = katalog_on_kontrol(
            self.conn,
            REQUIRED_HEADERS,
            rows,
        )

        after = {
            "urunler": self.conn.execute(
                "SELECT COUNT(*) FROM urunler"
            ).fetchone()[0],
            "receteler": self.conn.execute(
                "SELECT COUNT(*) FROM receteler"
            ).fetchone()[0],
        }

        self.assertTrue(report["gecerli"])
        self.assertEqual(
            report["ozet"]["urun_sayisi"],
            61,
        )
        self.assertEqual(
            report["ozet"]["recete_sayisi"],
            61,
        )
        self.assertEqual(before, after)

    def test_zero_water_and_dough_water_are_supported(self):
        rows = [
            self.valid_row(1),
            self.valid_row(
                2,
                parti_teorik_kg="2.000",
                proses_suyu_kg="1.000",
                miktar_kg="1.000",
            ),
        ]

        report = katalog_on_kontrol(
            self.conn,
            REQUIRED_HEADERS,
            rows,
        )

        self.assertTrue(report["gecerli"])
        self.assertEqual(
            report["ozet"]["recete_sayisi"],
            2,
        )

    def test_missing_and_inactive_material_rejected(self):
        rows = [
            self.valid_row(
                1,
                hammadde_adi="Sistemde Yok",
            ),
            self.valid_row(
                2,
                hammadde_adi="Pasif Hammadde",
            ),
        ]

        report = katalog_on_kontrol(
            self.conn,
            REQUIRED_HEADERS,
            rows,
        )
        codes = self.error_codes(report)

        self.assertFalse(report["gecerli"])
        self.assertIn("HAMMADDE_BULUNAMADI", codes)
        self.assertIn("HAMMADDE_PASIF", codes)

    def test_nonpositive_material_and_negative_water_rejected(
        self,
    ):
        rows = [
            self.valid_row(
                1,
                miktar_kg="0",
            ),
            self.valid_row(
                2,
                proses_suyu_kg="-0.001",
                parti_teorik_kg="0.999",
            ),
        ]

        report = katalog_on_kontrol(
            self.conn,
            REQUIRED_HEADERS,
            rows,
        )
        codes = self.error_codes(report)

        self.assertFalse(report["gecerli"])
        self.assertIn("POZITIF_OLMALI", codes)
        self.assertIn("ALT_SINIR", codes)

    def test_mass_balance_error_rejected(self):
        report = katalog_on_kontrol(
            self.conn,
            REQUIRED_HEADERS,
            [
                self.valid_row(
                    1,
                    parti_teorik_kg="2.000",
                    proses_suyu_kg="0.500",
                    miktar_kg="1.000",
                )
            ],
        )

        self.assertFalse(report["gecerli"])
        self.assertIn(
            "KUTLE_DENGESI",
            self.error_codes(report),
        )

    def test_duplicate_material_rejected(self):
        first = self.valid_row(1)
        second = self.valid_row(1)
        second["_satir"] = 3

        report = katalog_on_kontrol(
            self.conn,
            REQUIRED_HEADERS,
            [first, second],
        )

        self.assertFalse(report["gecerli"])
        self.assertIn(
            "YINELENEN_HAMMADDE",
            self.error_codes(report),
        )

    def test_second_active_recipe_rejected(self):
        first = self.valid_row(1)
        second = self.valid_row(
            1,
            recete_kodu="TEST001-ALT",
            recete_adi="TEST ÜRÜNÜ 001 ALTERNATİF",
            revizyon_no="01",
        )
        second["_satir"] = 3

        report = katalog_on_kontrol(
            self.conn,
            REQUIRED_HEADERS,
            [first, second],
        )

        self.assertFalse(report["gecerli"])
        self.assertIn(
            "IKINCI_AKTIF_RECETE",
            self.error_codes(report),
        )

    def test_empty_catalog_rejected(self):
        report = katalog_on_kontrol(
            self.conn,
            REQUIRED_HEADERS,
            [],
        )

        self.assertFalse(report["gecerli"])
        self.assertIn(
            "BOS_KATALOG",
            self.error_codes(report),
        )

    def test_invalid_revision_format_rejected(self):
        report = katalog_on_kontrol(
            self.conn,
            REQUIRED_HEADERS,
            [
                self.valid_row(
                    1,
                    revizyon_no="1",
                )
            ],
        )

        self.assertFalse(report["gecerli"])
        self.assertIn(
            "GECERSIZ_REVIZYON",
            self.error_codes(report),
        )

    def test_duplicate_product_name_rejected(self):
        first = self.valid_row(1)
        second = self.valid_row(
            2,
            urun_adi=first["urun_adi"],
        )

        report = katalog_on_kontrol(
            self.conn,
            REQUIRED_HEADERS,
            [first, second],
        )

        self.assertFalse(report["gecerli"])
        self.assertIn(
            "YINELENEN_URUN_ADI",
            self.error_codes(report),
        )

    def test_duplicate_barcode_rejected(self):
        first = self.valid_row(
            1,
            barkod="869000000001",
        )
        second = self.valid_row(
            2,
            barkod="869000000001",
        )

        report = katalog_on_kontrol(
            self.conn,
            REQUIRED_HEADERS,
            [first, second],
        )

        self.assertFalse(report["gecerli"])
        self.assertIn(
            "YINELENEN_BARKOD",
            self.error_codes(report),
        )

    def test_duplicate_recipe_name_rejected(self):
        first = self.valid_row(1)
        second = self.valid_row(
            2,
            recete_adi=first["recete_adi"],
        )

        report = katalog_on_kontrol(
            self.conn,
            REQUIRED_HEADERS,
            [first, second],
        )

        self.assertFalse(report["gecerli"])
        self.assertIn(
            "YINELENEN_RECETE_ADI",
            self.error_codes(report),
        )

    def test_csv_and_xlsx_read_same_contract(self):
        row = self.valid_row(1)
        values = {
            header: row.get(header, "")
            for header in ALL_HEADERS
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            csv_path = temp_path / "catalog.csv"
            xlsx_path = temp_path / "catalog.xlsx"

            with csv_path.open(
                "w",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=ALL_HEADERS,
                    delimiter=";",
                )
                writer.writeheader()
                writer.writerow(values)

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = CATALOG_SHEET_NAME
            sheet.append(list(ALL_HEADERS))
            sheet.append([
                values[header]
                for header in ALL_HEADERS
            ])
            workbook.save(xlsx_path)
            workbook.close()

            csv_report = katalog_dosyasi_on_kontrol(
                self.conn,
                csv_path,
            )
            xlsx_report = katalog_dosyasi_on_kontrol(
                self.conn,
                xlsx_path,
            )

        self.assertTrue(csv_report["gecerli"])
        self.assertTrue(xlsx_report["gecerli"])
        self.assertEqual(
            csv_report["ozet"],
            xlsx_report["ozet"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

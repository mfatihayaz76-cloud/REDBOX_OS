import hashlib
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import database.report_engine as report_engine


SCHEMA = """
CREATE TABLE urunler (
    id INTEGER PRIMARY KEY,
    urun_kodu TEXT NOT NULL,
    urun_adi TEXT NOT NULL,
    kategori TEXT,
    barkod TEXT,
    birim TEXT,
    raf_omru_gun INTEGER,
    saklama_sicakligi TEXT
);

CREATE TABLE personeller (
    id INTEGER PRIMARY KEY,
    ad_soyad TEXT NOT NULL
);

CREATE TABLE receteler (
    id INTEGER PRIMARY KEY,
    urun_id INTEGER NOT NULL,
    recete_kodu TEXT,
    ad TEXT NOT NULL,
    revizyon_no TEXT,
    gecerlilik_tarihi TEXT,
    durum TEXT NOT NULL,
    aktif INTEGER NOT NULL,
    parti_teorik_kg REAL NOT NULL,
    proses_suyu_kg REAL NOT NULL,
    revizyon_aciklamasi TEXT,
    olusturan_personel_id INTEGER,
    onaylayan_personel_id INTEGER,
    onay_zamani TEXT,
    icerik_sha256 TEXT
);

CREATE TABLE hammaddeler (
    id INTEGER PRIMARY KEY,
    ad TEXT NOT NULL
);

CREATE TABLE recete_kalemleri (
    id INTEGER PRIMARY KEY,
    recete_id INTEGER NOT NULL,
    hammadde_id INTEGER NOT NULL,
    miktar_kg REAL NOT NULL
);

CREATE TABLE dijital_onaylar (
    id INTEGER PRIMARY KEY,
    kaynak_turu TEXT NOT NULL,
    kaynak_id INTEGER NOT NULL,
    onay_turu TEXT NOT NULL,
    karar TEXT NOT NULL,
    kullanici_adi TEXT NOT NULL,
    ad_soyad TEXT NOT NULL,
    onay_zamani TEXT NOT NULL,
    aciklama TEXT,
    icerik_sha256 TEXT NOT NULL
);
"""


class RecipePDFContractTest(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

        self.conn.execute(
            """
            INSERT INTO urunler
            VALUES (
                1,
                'LP001',
                'Long Potato',
                'Dondurulmuş Patates Ürünü',
                '869000000001',
                'KG',
                365,
                '-18°C'
            )
            """
        )

        self.conn.executemany(
            """
            INSERT INTO personeller
            VALUES (?, ?)
            """,
            (
                (1, "Fatih Ayaz"),
                (2, "Eda Ayaz"),
            ),
        )

        self.conn.execute(
            """
            INSERT INTO receteler
            VALUES (
                10,
                1,
                'LP001-REC',
                'LONG POTATO ANA REÇETE REV 01',
                '01',
                '20.07.2027',
                'AKTIF',
                1,
                20.412,
                10.700,
                'Kontrollü reçete revizyonu',
                2,
                1,
                '19.07.2026 23:30:00',
                'content-sha'
            )
            """
        )

        self.conn.executemany(
            """
            INSERT INTO hammaddeler
            VALUES (?, ?)
            """,
            (
                (1, "Patates Unu"),
                (2, "Tuz"),
            ),
        )

        self.conn.executemany(
            """
            INSERT INTO recete_kalemleri
            VALUES (?, ?, ?, ?)
            """,
            (
                (1, 10, 1, 9.568),
                (2, 10, 2, 0.144),
            ),
        )

        self.conn.execute(
            """
            INSERT INTO dijital_onaylar
            VALUES (
                1,
                'RECETE',
                10,
                'RECETE_ONAYI',
                'ONAYLANDI',
                'fatih',
                'Fatih Ayaz',
                '19.07.2026 23:30:00',
                'Formül ve kütle dengesi onaylandı.',
                'content-sha'
            )
            """
        )

        self.conn.commit()

        self.before_dump = "\n".join(
            self.conn.iterdump()
        )

        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_pdf_yolu = (
            report_engine.pdf_yolu
        )

        report_engine.pdf_yolu = (
            lambda _prefix, _reference: (
                Path(self.temp_dir.name)
                / "REDBOX_OS_RECETE_FOYU.pdf"
            )
        )

    def tearDown(self):
        report_engine.pdf_yolu = (
            self.original_pdf_yolu
        )
        self.temp_dir.cleanup()
        self.conn.close()

    def _create_and_read(self):
        output = report_engine.recete_pdf_olustur(
            self.conn,
            10,
        )

        self.assertTrue(Path(output).exists())
        self.assertGreater(
            Path(output).stat().st_size,
            1000,
        )

        reader = PdfReader(str(output))
        text = "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

        return Path(output), reader, text

    def test_pdf_identity_and_formula_contract(self):
        _output, _reader, text = (
            self._create_and_read()
        )

        required = (
            "KONTROLLÜ REÇETE FÖYÜ",
            "LP001",
            "LP001-REC",
            "Long Potato",
            "Patates Unu",
            "Proses Suyu",
        )

        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_mass_balance_and_non_stock_water(self):
        _output, _reader, text = (
            self._create_and_read()
        )

        required = (
            "20.412 kg",
            "10.700 kg",
            "Stok Dışı",
            "Kütle Dengesi Sonucu",
            "UYGUN",
        )

        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_digital_approval_contract(self):
        _output, _reader, text = (
            self._create_and_read()
        )

        required = (
            "ONAYLANDI",
            "Fatih Ayaz",
            "İçerik SHA-256",
            "content-sha",
        )

        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_controlled_section_page_break(self):
        _output, reader, _text = self._create_and_read()

        self.assertEqual(len(reader.pages), 2)

        first_page = reader.pages[0].extract_text() or ""
        second_page = reader.pages[1].extract_text() or ""

        self.assertIn(
            "1 Parti Formülasyonu",
            first_page,
        )
        self.assertNotIn(
            "Kütle Dengesi",
            first_page,
        )
        self.assertIn(
            "Kütle Dengesi",
            second_page,
        )
        self.assertIn(
            "Revizyon ve Dijital Onay",
            second_page,
        )
        self.assertIn(
            "İçerik SHA-256",
            second_page,
        )

    def test_pdf_generation_is_read_only(self):
        self._create_and_read()

        after_dump = "\n".join(
            self.conn.iterdump()
        )

        self.assertEqual(
            self.before_dump,
            after_dump,
        )

    def test_unknown_recipe_is_rejected(self):
        with self.assertRaises(ValueError):
            report_engine.recete_pdf_olustur(
                self.conn,
                999,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path('/Users/test/Desktop/REDBOX_OS/database/redbox_os.db')


def table_count(conn, table):
    return conn.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]


def scalar(conn, sql, params=()):
    row = conn.execute(
        sql,
        params,
    ).fetchone()

    if row is None:
        return 0

    value = row[0]

    if value is None:
        return 0

    return value


def table_exists(conn, table):
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table,),
    ).fetchone()

    return row is not None


def columns(conn, table):
    return [
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    ]


def print_table_contract(conn, table):
    print("")
    print(f"=== {table.upper()} SOZLESMESI ===")

    if not table_exists(conn, table):
        print("YOK")
        return

    print(
        "SATIR:",
        table_count(conn, table),
    )

    print(
        "KOLONLAR:",
        columns(conn, table),
    )


def main():
    print(
        "=== REDBOX OS PHASE 3 "
        "FINAL CAPRAZ DENETIM ==="
    )

    print("")
    print("DB:", DB_PATH)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DB BULUNAMADI: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        tables = [
            "depo_kabul",
            "hammaddeler",
            "uretim",
            "uretim_hammadde_lotlari",
            "uretim_recete",
            "paketleme",
            "musteriler",
            "sevkiyat",
            "sevkiyat_kalemleri",
            "mamul_stok_hareketleri",
        ]

        print("")
        print("=== TABLO SAYIMLARI ===")

        for table in tables:
            if table_exists(conn, table):
                print(
                    f"{table:<32}: "
                    f"{table_count(conn, table)}"
                )
            else:
                print(
                    f"{table:<32}: YOK"
                )

        print("")
        print("=== FOREIGN KEY CHECK ===")

        fk_rows = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if fk_rows:
            for row in fk_rows:
                print(tuple(row))

            raise ValueError(
                "FOREIGN KEY HATASI VAR"
            )

        print("OK: FOREIGN KEY CHECK")

        print("")
        print("=== URETIM TOPLAMLARI ===")

        uretim_cols = columns(
            conn,
            "uretim",
        )

        print(
            "URETIM KOLONLARI:",
            uretim_cols,
        )

        if "parti_teorik_kg" in uretim_cols:
            teorik = float(
                scalar(
                    conn,
                    """
                    SELECT COALESCE(
                        SUM(parti_teorik_kg),
                        0
                    )
                    FROM uretim
                    """
                )
            )

            print(
                "TOPLAM TEORIK:",
                f"{teorik:.3f}",
                "KG",
            )

        if "net_uretim_kg" in uretim_cols:
            net = float(
                scalar(
                    conn,
                    """
                    SELECT COALESCE(
                        SUM(net_uretim_kg),
                        0
                    )
                    FROM uretim
                    """
                )
            )

            print(
                "TOPLAM NET URETIM:",
                f"{net:.3f}",
                "KG",
            )

        elif "net_kg" in uretim_cols:
            net = float(
                scalar(
                    conn,
                    """
                    SELECT COALESCE(
                        SUM(net_kg),
                        0
                    )
                    FROM uretim
                    """
                )
            )

            print(
                "TOPLAM NET URETIM:",
                f"{net:.3f}",
                "KG",
            )

        print("")
        print("=== PAKETLEME TOPLAMLARI ===")

        paketli_kg = float(
            scalar(
                conn,
                """
                SELECT COALESCE(
                    SUM(paketlenen_kg),
                    0
                )
                FROM paketleme
                """
            )
        )

        paket_fire = float(
            scalar(
                conn,
                """
                SELECT COALESCE(
                    SUM(paketleme_firesi_kg),
                    0
                )
                FROM paketleme
                """
            )
        )

        print(
            "TOPLAM PAKETLI:",
            f"{paketli_kg:.3f}",
            "KG",
        )

        print(
            "TOPLAM PAKETLEME FIRESI:",
            f"{paket_fire:.3f}",
            "KG",
        )

        print("")
        print("=== SEVKIYAT TOPLAMLARI ===")

        sevk_kg = float(
            scalar(
                conn,
                """
                
SELECT COALESCE(
                    SUM(sevk_kg),
                    0
                )
                FROM sevkiyat_kalemleri

                """
            )
        )

        print(
            "TOPLAM SEVK:",
            f"{sevk_kg:.3f}",
            "KG",
        )

        print("")
        print("=== MAMUL KUTLE DENKLIGI ===")

        mamul_stok = (
            paketli_kg
            - sevk_kg
        )

        print(
            "PAKETLI:",
            f"{paketli_kg:.3f}",
            "KG",
        )

        print(
            "SEVK:",
            f"{sevk_kg:.3f}",
            "KG",
        )

        print(
            "HESAPLANAN MAMUL STOK:",
            f"{mamul_stok:.3f}",
            "KG",
        )

        if abs(
            paketli_kg - 2362.000
        ) > 0.001:
            raise ValueError(
                "PAKETLI MAMUL "
                "2362.000 KG DEGIL"
            )

        if abs(
            paket_fire - 7.496
        ) > 0.001:
            raise ValueError(
                "PAKETLEME FIRESI "
                "7.496 KG DEGIL"
            )

        if abs(
            sevk_kg - 2352.000
        ) > 0.001:
            raise ValueError(
                "TOPLAM SEVK "
                "2352.000 KG DEGIL"
            )

        if abs(
            mamul_stok - 10.000
        ) > 0.001:
            raise ValueError(
                "MAMUL STOK "
                "10.000 KG DEGIL"
            )

        print("")
        print(
            "OK: PAKETLI MAMUL "
            "2362.000 KG"
        )

        print(
            "OK: PAKETLEME FIRESI "
            "7.496 KG"
        )

        print(
            "OK: SEVKIYAT "
            "2352.000 KG"
        )

        print(
            "OK: MAMUL STOK "
            "10.000 KG"
        )

        print("")
        print(
            "=== SEVKIYAT KALEMI "
            "KG DENKLIGI ==="
        )

        rows = conn.execute(
            """
            SELECT
                s.id,
                s.sevkiyat_tarihi,
                sk.sevk_kg,
                COALESCE(
                    SUM(
                        sk.paket_adedi
                        * sk.ambalaj_gram
                        / 1000.0
                    ),
                    0
                ) AS kalem_kg
            FROM sevkiyat s
                JOIN sevkiyat_kalemleri sk
                    ON sk.sevkiyat_id = s.id
            LEFT JOIN sevkiyat_kalemleri sk
              ON sk.sevkiyat_id = s.id
            GROUP BY
                s.id,
                s.sevkiyat_tarihi,
                sk.sevk_kg
            ORDER BY
                s.sevkiyat_tarihi,
                s.id
            """
        ).fetchall()

        for row in rows:
            fark = (
                float(row["sevk_kg"])
                - float(row["kalem_kg"])
            )

            durum = (
                "KAPALI"
                if abs(fark) <= 0.001
                else "HATA"
            )

            print(
                row["sevkiyat_tarihi"],
                "| SEVK:",
                f"{float(row['sevk_kg']):.3f}",
                "| KALEM:",
                f"{float(row['kalem_kg']):.3f}",
                "| FARK:",
                f"{fark:.3f}",
                "|",
                durum,
            )

            if abs(fark) > 0.001:
                raise ValueError(
                    "SEVKIYAT KALEM "
                    "KUTLE DENKLIGI BOZUK"
                )

        print("")
        print(
            "OK: TUM SEVKIYAT "
            "KALEM DENKLIKLERI KAPALI"
        )

        print("")
        print(
            "=== PAKETLEME LOT "
            "STOK KONTROLU ==="
        )

        stok_rows = conn.execute(
            """
            SELECT
                p.id AS paketleme_id,
                u.uretim_tarihi,
                u.lot_no,
                p.ambalaj_gram,
                p.paket_adedi,
                COALESCE(
                    SUM(sk.paket_adedi),
                    0
                ) AS sevk_paket,
                (
                    p.paket_adedi
                    - COALESCE(
                        SUM(sk.paket_adedi),
                        0
                    )
                ) AS kalan_paket
            FROM paketleme p
            JOIN uretim u
              ON u.id = p.uretim_id
            LEFT JOIN sevkiyat_kalemleri sk
              ON sk.paketleme_id = p.id
            GROUP BY
                p.id,
                u.uretim_tarihi,
                u.lot_no,
                p.ambalaj_gram,
                p.paket_adedi
            ORDER BY
                u.uretim_tarihi,
                p.ambalaj_gram
            """
        ).fetchall()

        toplam_stok_kg = 0.0

        for row in stok_rows:
            kalan_paket = int(
                row["kalan_paket"]
            )

            if kalan_paket < 0:
                raise ValueError(
                    "NEGATIF MAMUL STOK: "
                    f"{row['lot_no']} | "
                    f"{row['ambalaj_gram']} G | "
                    f"{kalan_paket} PAKET"
                )

            kalan_kg = (
                kalan_paket
                * int(row["ambalaj_gram"])
                / 1000
            )

            toplam_stok_kg += kalan_kg

            print(
                row["uretim_tarihi"],
                "| LOT:",
                row["lot_no"],
                "|",
                f"{row['ambalaj_gram']} G",
                "| PAKETLENEN:",
                row["paket_adedi"],
                "| SEVK:",
                row["sevk_paket"],
                "| KALAN:",
                kalan_paket,
                "| KG:",
                f"{kalan_kg:.3f}",
            )

        print("")
        print(
            "LOT BAZLI TOPLAM "
            "MAMUL STOK:",
            f"{toplam_stok_kg:.3f}",
            "KG",
        )

        if abs(
            toplam_stok_kg - 10.000
        ) > 0.001:
            raise ValueError(
                "LOT BAZLI MAMUL STOK "
                "10.000 KG DEGIL"
            )

        print(
            "OK: LOT BAZLI MAMUL "
            "STOK 10.000 KG"
        )

        print("")
        print(
            "=== TEMEL TABLO "
            "SOZLESMELERI ==="
        )

        for table in tables:
            print_table_contract(
                conn,
                table,
            )

        print("")
        print(
            "=== PHASE 3 FINAL SONUC ==="
        )

        print(
            "OK: SQL FOREIGN KEY TEMIZ"
        )

        print(
            "OK: PAKETLEME KUTLESI KAPALI"
        )

        print(
            "OK: SEVKIYAT KUTLESI KAPALI"
        )

        print(
            "OK: SEVKIYAT KALEMLERI KAPALI"
        )

        print(
            "OK: FIFO LOT STOKLARI NEGATIF DEGIL"
        )

        print(
            "OK: MAMUL DONEM SONU STOK "
            "10.000 KG"
        )

        print("")
        print(
            "PHASE 3 FINAL CAPRAZ "
            "DENETIM BASARILI"
        )

        print("")
        print(
            "NOT: SQL VERISI DEGISTIRILMEDI"
        )

        print(
            "NOT: EXCEL DEGISTIRILMEDI"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()

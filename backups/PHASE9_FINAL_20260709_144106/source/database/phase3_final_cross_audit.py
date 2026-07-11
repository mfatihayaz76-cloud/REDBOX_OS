import sqlite3
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE
    / "database"
    / "redbox_os.db"
)


def scalar(
    conn,
    sql,
    params=(),
):
    row = conn.execute(
        sql,
        params,
    ).fetchone()

    if row is None:
        return None

    return row[0]


def tablo_sayimi(
    conn,
    tablo,
):
    return int(
        scalar(
            conn,
            f"""
            SELECT COUNT(*)
            FROM {tablo}
            """,
        )
    )


def assert_close(
    gercek,
    beklenen,
    mesaj,
    tolerans=0.001,
):
    if abs(
        float(gercek)
        - float(beklenen)
    ) > tolerans:
        raise ValueError(
            f"{mesaj}: "
            f"{float(gercek):.3f} "
            f"!= "
            f"{float(beklenen):.3f}"
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
            f"DB YOK: {DB_PATH}"
        )

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    try:
        conn.execute(
            "PRAGMA foreign_keys = ON"
        )

        print("")
        print(
            "=== TABLO SAYIMLARI ==="
        )

        tablolar = [
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

        sayimlar = {}

        for tablo in tablolar:
            adet = tablo_sayimi(
                conn,
                tablo,
            )

            sayimlar[tablo] = adet

            print(
                f"{tablo:<32}: "
                f"{adet}"
            )

        print("")
        print(
            "=== FOREIGN KEY CHECK ==="
        )

        fk_rows = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if fk_rows:
            print(
                "FOREIGN KEY HATALARI:"
            )

            for row in fk_rows:
                print(
                    tuple(row)
                )

            raise ValueError(
                "FOREIGN KEY CHECK BASARISIZ"
            )

        print(
            "OK: FOREIGN KEY CHECK"
        )

        print("")
        print(
            "=== URETIM TOPLAMLARI ==="
        )

        uretim_kg = float(
            scalar(
                conn,
                """
                SELECT COALESCE(
                    SUM(net_uretim_kg),
                    0
                )
                FROM uretim
                """,
            )
        )

        print(
            "TOPLAM NET URETIM:",
            f"{uretim_kg:.3f}",
            "KG",
        )

        print("")
        print(
            "=== PAKETLEME TOPLAMLARI ==="
        )

        paketli_kg = float(
            scalar(
                conn,
                """
                SELECT COALESCE(
                    SUM(paketlenen_kg),
                    0
                )
                FROM paketleme
                """,
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
                """,
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
        print(
            "=== URETIM -> PAKETLEME "
            "KUTLE DENKLIGI ==="
        )

        uretim_paket_fark = (
            uretim_kg
            - paketli_kg
            - paket_fire
        )

        print(
            "NET URETIM:",
            f"{uretim_kg:.3f}",
            "KG",
        )

        print(
            "PAKETLI:",
            f"{paketli_kg:.3f}",
            "KG",
        )

        print(
            "PAKETLEME FIRESI:",
            f"{paket_fire:.3f}",
            "KG",
        )

        print(
            "FARK:",
            f"{uretim_paket_fark:.3f}",
            "KG",
        )

        assert_close(
            uretim_paket_fark,
            0.000,
            (
                "URETIM PAKETLEME "
                "KUTLE DENKLIGI KAPANMADI"
            ),
        )

        print(
            "OK: URETIM PAKETLEME "
            "KUTLE DENKLIGI KAPALI"
        )

        print("")
        print(
            "=== SEVKIYAT TOPLAMLARI ==="
        )

        sevk_kg = float(
            scalar(
                conn,
                """
                SELECT COALESCE(
                    SUM(sk.sevk_kg),
                    0
                )
                FROM sevkiyat_kalemleri sk
                """,
            )
        )

        print(
            "TOPLAM SEVK:",
            f"{sevk_kg:.3f}",
            "KG",
        )

        print("")
        print(
            "=== MAMUL KUTLE DENKLIGI ==="
        )

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

        assert_close(
            paketli_kg,
            2362.000,
            "TOPLAM PAKETLI",
        )

        assert_close(
            paket_fire,
            7.496,
            "TOPLAM PAKETLEME FIRESI",
        )

        assert_close(
            sevk_kg,
            2352.000,
            "TOPLAM SEVK",
        )

        assert_close(
            mamul_stok,
            10.000,
            "MAMUL DONEM SONU STOK",
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
                sk.id
                    AS sevkiyat_kalemi_id,
                s.id
                    AS sevkiyat_id,
                s.sevkiyat_tarihi
                    AS sevkiyat_tarihi,
                s.musteri
                    AS musteri,
                p.id
                    AS paketleme_id,
                p.ambalaj_gram
                    AS ambalaj_gram,
                sk.paket_adedi
                    AS paket_adedi,
                sk.sevk_kg
                    AS sevk_kg
            FROM sevkiyat_kalemleri sk
            JOIN sevkiyat s
                ON s.id = sk.sevkiyat_id
            JOIN paketleme p
                ON p.id = sk.paketleme_id
            ORDER BY
                s.id,
                sk.id
            """
        ).fetchall()

        toplam_hesap_kg = 0.0

        for row in rows:
            hesap_kg = (
                int(
                    row["paket_adedi"]
                )
                * int(
                    row["ambalaj_gram"]
                )
                / 1000
            )

            kayit_kg = float(
                row["sevk_kg"]
            )

            fark = (
                kayit_kg
                - hesap_kg
            )

            print(
                f"{row['sevkiyat_tarihi']} | "
                f"{row['musteri']} | "
                f"PAKETLEME ID "
                f"{row['paketleme_id']} | "
                f"{row['ambalaj_gram']} G | "
                f"PAKET: "
                f"{row['paket_adedi']} | "
                f"KAYIT KG: "
                f"{kayit_kg:.3f} | "
                f"HESAP KG: "
                f"{hesap_kg:.3f} | "
                f"FARK: "
                f"{fark:.3f}"
            )

            assert_close(
                kayit_kg,
                hesap_kg,
                (
                    "SEVKIYAT KALEMI "
                    "KG DENKLIGI HATASI "
                    f"ID {row['sevkiyat_kalemi_id']}"
                ),
            )

            toplam_hesap_kg += (
                hesap_kg
            )

        assert_close(
            toplam_hesap_kg,
            sevk_kg,
            (
                "SEVKIYAT KALEMLERI "
                "TOPLAM KG DENKLIGI"
            ),
        )

        print("")
        print(
            "OK: TUM SEVKIYAT "
            "KALEMLERI KG DENK"
        )

        print(
            "OK: HESAPLANAN KALEM TOPLAMI:",
            f"{toplam_hesap_kg:.3f}",
            "KG",
        )

        print("")
        print(
            "=== PAKETLEME STOK "
            "ASIM DENETIMI ==="
        )

        stok_rows = conn.execute(
            """
            SELECT
                p.id
                    AS paketleme_id,
                u.uretim_tarihi
                    AS uretim_tarihi,
                u.urun_lot_no
                    AS urun_lot_no,
                p.ambalaj_gram
                    AS ambalaj_gram,
                p.paket_adedi
                    AS paketlenen_paket,
                COALESCE(
                    SUM(sk.paket_adedi),
                    0
                )
                    AS sevk_paket
            FROM paketleme p
            JOIN uretim u
                ON u.id = p.uretim_id
            LEFT JOIN sevkiyat_kalemleri sk
                ON sk.paketleme_id = p.id
            GROUP BY
                p.id,
                u.uretim_tarihi,
                u.urun_lot_no,
                p.ambalaj_gram,
                p.paket_adedi
            ORDER BY
                u.id,
                p.id
            """
        ).fetchall()

        toplam_kalan_kg = 0.0

        for row in stok_rows:
            paketlenen = int(
                row["paketlenen_paket"]
            )

            sevk = int(
                row["sevk_paket"]
            )

            kalan = (
                paketlenen
                - sevk
            )

            if kalan < 0:
                raise ValueError(
                    "NEGATIF MAMUL STOK: "
                    f"PAKETLEME ID "
                    f"{row['paketleme_id']} | "
                    f"KALAN {kalan} PAKET"
                )

            kalan_kg = (
                kalan
                * int(
                    row["ambalaj_gram"]
                )
                / 1000
            )

            toplam_kalan_kg += (
                kalan_kg
            )

            print(
                f"{row['uretim_tarihi']} | "
                f"LOT: "
                f"{row['urun_lot_no']} | "
                f"{row['ambalaj_gram']} G | "
                f"PAKETLENEN: "
                f"{paketlenen} | "
                f"SEVK: "
                f"{sevk} | "
                f"KALAN: "
                f"{kalan} | "
                f"KALAN KG: "
                f"{kalan_kg:.3f}"
            )

        assert_close(
            toplam_kalan_kg,
            mamul_stok,
            (
                "LOT BAZLI MAMUL STOK "
                "GENEL STOKLA ESLESMIYOR"
            ),
        )

        print("")
        print(
            "OK: NEGATIF MAMUL STOK YOK"
        )

        print(
            "OK: LOT BAZLI MAMUL STOK:",
            f"{toplam_kalan_kg:.3f}",
            "KG",
        )

        print("")
        print(
            "=== SEVKIYAT BASLIK "
            "KALEM DENETIMI ==="
        )

        sevkiyat_rows = conn.execute(
            """
            SELECT
                s.id
                    AS sevkiyat_id,
                s.sevkiyat_tarihi
                    AS sevkiyat_tarihi,
                s.musteri
                    AS musteri,
                COUNT(sk.id)
                    AS kalem_adedi,
                COALESCE(
                    SUM(sk.paket_adedi),
                    0
                )
                    AS toplam_paket,
                COALESCE(
                    SUM(sk.sevk_kg),
                    0
                )
                    AS toplam_kg
            FROM sevkiyat s
            LEFT JOIN sevkiyat_kalemleri sk
                ON sk.sevkiyat_id = s.id
            GROUP BY
                s.id,
                s.sevkiyat_tarihi,
                s.musteri
            ORDER BY
                s.id
            """
        ).fetchall()

        for row in sevkiyat_rows:
            if int(
                row["kalem_adedi"]
            ) <= 0:
                raise ValueError(
                    "KALEMSIZ SEVKIYAT: "
                    f"ID {row['sevkiyat_id']}"
                )

            print(
                f"{row['sevkiyat_tarihi']} | "
                f"{row['musteri']} | "
                f"KALEM: "
                f"{row['kalem_adedi']} | "
                f"PAKET: "
                f"{row['toplam_paket']} | "
                f"KG: "
                f"{float(row['toplam_kg']):.3f}"
            )

        print("")
        print(
            "OK: KALEMSIZ SEVKIYAT YOK"
        )

        print("")
        print(
            "=== PHASE 3 FINAL SONUC ==="
        )

        print(
            "OK: FOREIGN KEY"
        )

        print(
            "OK: URETIM -> PAKETLEME "
            "KUTLE DENKLIGI"
        )

        print(
            "OK: PAKETLEME -> SEVKIYAT "
            "MAMUL DENKLIGI"
        )

        print(
            "OK: SEVKIYAT KALEMI "
            "KG DENKLIGI"
        )

        print(
            "OK: NEGATIF MAMUL STOK YOK"
        )

        print(
            "OK: LOT BAZLI MAMUL STOK "
            "10.000 KG"
        )

        print(
            "OK: KALEMSIZ SEVKIYAT YOK"
        )

        print("")
        print(
            "REDBOX OS PHASE 3 "
            "FINAL CAPRAZ DENETIM BASARILI"
        )

        print("")
        print(
            "NOT: SQL VERISI DEGISTIRILMEDI"
        )

        print(
            "NOT: EXCEL DEGISTIRILMEDI"
        )

        print(
            "NOT: PHASE 2 IMPORT "
            "DEGISTIRILMEDI"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()

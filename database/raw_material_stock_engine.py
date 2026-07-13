import sqlite3

from database.db import get_connection


TOLERANS = 0.000001


def hammadde_lot_stoklari(
    sadece_pozitif=False
):
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT
                dk.id AS depo_kabul_id,
                dk.hammadde_id,
                h.ad AS hammadde,
                dk.kabul_tarihi,
                dk.tedarikci,
                dk.tedarikci_lot_no,
                dk.uretim_tarihi,
                dk.skt_tett,
                dk.miktar_kg AS kabul_kg,
                COALESCE(
                    SUM(
                        uhl.kullanilan_miktar_kg
                    ),
                    0
                ) AS tuketim_kg,
                COALESCE(
                    (
                        SELECT SUM(
                            CASE
                                WHEN hsh.yon = 'GIRIS'
                                THEN hsh.miktar_kg
                                WHEN hsh.yon = 'CIKIS'
                                THEN -hsh.miktar_kg
                                ELSE 0
                            END
                        )
                        FROM hammadde_stok_hareketleri hsh
                        WHERE hsh.depo_kabul_id = dk.id
                    ),
                    0
                ) AS hareket_net_kg,
                (
                    dk.miktar_kg
                    -
                    COALESCE(
                        SUM(
                            uhl.kullanilan_miktar_kg
                        ),
                        0
                    )
                    +
                    COALESCE(
                        (
                            SELECT SUM(
                                CASE
                                    WHEN hsh.yon = 'GIRIS'
                                    THEN hsh.miktar_kg
                                    WHEN hsh.yon = 'CIKIS'
                                    THEN -hsh.miktar_kg
                                    ELSE 0
                                END
                            )
                            FROM hammadde_stok_hareketleri hsh
                            WHERE hsh.depo_kabul_id = dk.id
                        ),
                        0
                    )
                ) AS kalan_kg
            FROM depo_kabul dk
            JOIN hammaddeler h
                ON h.id = dk.hammadde_id
            LEFT JOIN uretim_hammadde_lotlari uhl
                ON uhl.depo_kabul_id = dk.id
            WHERE
                dk.kabul_durumu = 'KABUL'
            GROUP BY
                dk.id,
                dk.hammadde_id,
                h.ad,
                dk.kabul_tarihi,
                dk.tedarikci,
                dk.tedarikci_lot_no,
                dk.uretim_tarihi,
                dk.skt_tett,
                dk.miktar_kg
            ORDER BY
                h.ad,
                dk.id
            """
        ).fetchall()

        sonuc = []

        for row in rows:
            item = dict(row)

            item["kabul_kg"] = float(
                item["kabul_kg"]
            )

            item["tuketim_kg"] = float(
                item["tuketim_kg"]
            )

            item["hareket_net_kg"] = float(
                item["hareket_net_kg"]
            )

            item["kalan_kg"] = float(
                item["kalan_kg"]
            )

            if (
                sadece_pozitif
                and item["kalan_kg"] <= TOLERANS
            ):
                continue

            sonuc.append(
                item
            )

        return sonuc

    finally:
        conn.close()


def hammadde_stok_ozeti():
    conn = get_connection()

    try:
        active_rows = conn.execute("""
            SELECT id, ad
            FROM hammaddeler
            WHERE aktif = 1
            ORDER BY id
        """).fetchall()
    finally:
        conn.close()

    lot_rows = hammadde_lot_stoklari()
    totals = {}

    for row in lot_rows:
        item = totals.setdefault(
            row["hammadde_id"],
            {
                "kabul_kg": 0.0,
                "tuketim_kg": 0.0,
                "hareket_net_kg": 0.0,
                "kalan_kg": 0.0,
            },
        )
        item["kabul_kg"] += row["kabul_kg"]
        item["tuketim_kg"] += row["tuketim_kg"]
        item["hareket_net_kg"] += row["hareket_net_kg"]
        item["kalan_kg"] += row["kalan_kg"]

    sonuc = []

    for row in active_rows:
        item = totals.get(
            row["id"],
            {
                "kabul_kg": 0.0,
                "tuketim_kg": 0.0,
                "hareket_net_kg": 0.0,
                "kalan_kg": 0.0,
            },
        )

        sonuc.append(
            {
                "hammadde_id": row["id"],
                "hammadde": row["ad"],
                **item,
            }
        )

    return sonuc

def hammadde_toplam_stok_kg():
    return sum(
        row["kalan_kg"]
        for row in hammadde_stok_ozeti()
    )


def negatif_hammadde_lotlari():
    return [
        row
        for row in hammadde_lot_stoklari()
        if row["kalan_kg"] < -TOLERANS
    ]


def hammadde_stok_dogrula():
    negatif = negatif_hammadde_lotlari()

    if negatif:
        detay = []

        for row in negatif:
            detay.append(
                (
                    row["hammadde"],
                    row["tedarikci_lot_no"],
                    row["kalan_kg"]
                )
            )

        raise ValueError(
            "Negatif hammadde lot stoku: "
            f"{detay}"
        )

    return True

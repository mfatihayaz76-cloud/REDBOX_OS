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
                (
                    dk.miktar_kg
                    -
                    COALESCE(
                        SUM(
                            uhl.kullanilan_miktar_kg
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
        rows = conn.execute(
            """
            SELECT
                h.id AS hammadde_id,
                h.ad AS hammadde,
                COALESCE(
                    kabul.kabul_kg,
                    0
                ) AS kabul_kg,
                COALESCE(
                    tuketim.tuketim_kg,
                    0
                ) AS tuketim_kg,
                (
                    COALESCE(
                        kabul.kabul_kg,
                        0
                    )
                    -
                    COALESCE(
                        tuketim.tuketim_kg,
                        0
                    )
                ) AS kalan_kg
            FROM hammaddeler h

            LEFT JOIN (
                SELECT
                    hammadde_id,
                    SUM(miktar_kg) AS kabul_kg
                FROM depo_kabul
                WHERE
                    kabul_durumu = 'KABUL'
                GROUP BY
                    hammadde_id
            ) kabul
                ON kabul.hammadde_id = h.id

            LEFT JOIN (
                SELECT
                    dk.hammadde_id,
                    SUM(
                        uhl.kullanilan_miktar_kg
                    ) AS tuketim_kg
                FROM uretim_hammadde_lotlari uhl
                JOIN depo_kabul dk
                    ON dk.id = uhl.depo_kabul_id
                GROUP BY
                    dk.hammadde_id
            ) tuketim
                ON tuketim.hammadde_id = h.id

            WHERE
                h.aktif = 1

            ORDER BY
                h.id
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

            item["kalan_kg"] = float(
                item["kalan_kg"]
            )

            sonuc.append(
                item
            )

        return sonuc

    finally:
        conn.close()


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

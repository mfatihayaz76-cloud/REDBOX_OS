from database.db import get_connection


def aktif_recete_getir(conn):
    recete = conn.execute("""
        SELECT id, ad, parti_teorik_kg
        FROM receteler
        WHERE aktif = 1
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    if recete is None:
        raise ValueError("Aktif üretim reçetesi bulunamadı.")

    return recete


def recete_ihtiyaclari_getir(conn, recete_id, parti_sayisi):
    kalemler = conn.execute("""
        SELECT
            rk.hammadde_id,
            h.ad AS hammadde,
            rk.miktar_kg
        FROM recete_kalemleri rk
        JOIN hammaddeler h
          ON h.id = rk.hammadde_id
        WHERE rk.recete_id = ?
        ORDER BY rk.id
    """, (recete_id,)).fetchall()

    return [
        {
            "hammadde_id": kalem["hammadde_id"],
            "hammadde": kalem["hammadde"],
            "ihtiyac_kg": float(kalem["miktar_kg"]) * parti_sayisi,
        }
        for kalem in kalemler
    ]


def lot_kalan_miktar(conn, depo_kabul_id):
    kabul = conn.execute("""
        SELECT miktar_kg
        FROM depo_kabul
        WHERE id = ?
    """, (depo_kabul_id,)).fetchone()

    if kabul is None:
        raise ValueError(
            f"Depo kabul kaydı bulunamadı: {depo_kabul_id}"
        )

    kullanilan = conn.execute("""
        SELECT COALESCE(SUM(kullanilan_miktar_kg), 0) AS toplam
        FROM uretim_hammadde_lotlari
        WHERE depo_kabul_id = ?
    """, (depo_kabul_id,)).fetchone()["toplam"]

    return float(kabul["miktar_kg"]) - float(kullanilan)


def uygun_lotlar_getir(conn, hammadde_id):
    return conn.execute("""
        SELECT
            dk.id,
            dk.kabul_tarihi,
            dk.tedarikci_lot_no,
            dk.miktar_kg
        FROM depo_kabul dk
        WHERE dk.hammadde_id = ?
          AND dk.kabul_durumu = 'KABUL'
        ORDER BY
            substr(dk.kabul_tarihi, 7, 4),
            substr(dk.kabul_tarihi, 4, 2),
            substr(dk.kabul_tarihi, 1, 2),
            dk.id
    """, (hammadde_id,)).fetchall()


def stok_kontrol(conn, recete_id, parti_sayisi):
    eksikler = []

    for ihtiyac in recete_ihtiyaclari_getir(
        conn,
        recete_id,
        parti_sayisi
    ):
        mevcut = 0.0

        for lot in uygun_lotlar_getir(
            conn,
            ihtiyac["hammadde_id"]
        ):
            kalan = lot_kalan_miktar(conn, lot["id"])

            if kalan > 0:
                mevcut += kalan

        if mevcut + 0.000001 < ihtiyac["ihtiyac_kg"]:
            eksikler.append({
                "hammadde": ihtiyac["hammadde"],
                "ihtiyac_kg": ihtiyac["ihtiyac_kg"],
                "mevcut_kg": mevcut,
                "eksik_kg": ihtiyac["ihtiyac_kg"] - mevcut,
            })

    return eksikler


def fifo_lot_tuket(conn, uretim_id, recete_id, parti_sayisi):
    eksikler = stok_kontrol(
        conn,
        recete_id,
        parti_sayisi
    )

    if eksikler:
        mesajlar = []

        for eksik in eksikler:
            mesajlar.append(
                f'{eksik["hammadde"]}: '
                f'ihtiyaç {eksik["ihtiyac_kg"]:.3f} kg, '
                f'mevcut {eksik["mevcut_kg"]:.3f} kg, '
                f'eksik {eksik["eksik_kg"]:.3f} kg'
            )

        raise ValueError(
            "HAMMADDE STOK YETERSIZ:\n" +
            "\n".join(mesajlar)
        )

    for ihtiyac in recete_ihtiyaclari_getir(
        conn,
        recete_id,
        parti_sayisi
    ):
        kalan_ihtiyac = ihtiyac["ihtiyac_kg"]

        for lot in uygun_lotlar_getir(
            conn,
            ihtiyac["hammadde_id"]
        ):
            lot_kalan = lot_kalan_miktar(
                conn,
                lot["id"]
            )

            if lot_kalan <= 0:
                continue

            kullanilacak = min(
                lot_kalan,
                kalan_ihtiyac
            )

            conn.execute("""
                INSERT INTO uretim_hammadde_lotlari (
                    uretim_id,
                    depo_kabul_id,
                    kullanilan_miktar_kg
                )
                VALUES (?, ?, ?)
            """, (
                uretim_id,
                lot["id"],
                kullanilacak
            ))

            kalan_ihtiyac -= kullanilacak

            if kalan_ihtiyac <= 0.000001:
                break


def uretim_stok_isle(conn, uretim_id, parti_sayisi):
    recete = aktif_recete_getir(conn)

    fifo_lot_tuket(
        conn,
        uretim_id,
        recete["id"],
        parti_sayisi
    )

    conn.execute("""
        INSERT INTO uretim_recete (
            uretim_id,
            recete_id
        )
        VALUES (?, ?)
    """, (
        uretim_id,
        recete["id"]
    ))

    return recete

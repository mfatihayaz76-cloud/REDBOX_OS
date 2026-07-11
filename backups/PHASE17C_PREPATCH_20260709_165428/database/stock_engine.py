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


def lot_parti_plani_oner(conn, parti_sayisi):
    recete = aktif_recete_getir(conn)
    plan = []

    for ihtiyac in recete_ihtiyaclari_getir(
        conn,
        recete["id"],
        parti_sayisi
    ):
        parti_kg = (
            float(ihtiyac["ihtiyac_kg"])
            / float(parti_sayisi)
        )

        kalan_parti = parti_sayisi
        parti_baslangic = 1

        for lot in uygun_lotlar_getir(
            conn,
            ihtiyac["hammadde_id"]
        ):
            lot_kalan = lot_kalan_miktar(
                conn,
                lot["id"]
            )

            if lot_kalan <= 0.000001:
                continue

            tam_parti = int(
                (lot_kalan + 0.000001)
                // parti_kg
            )

            if tam_parti <= 0:
                continue

            kullanilacak_parti = min(
                tam_parti,
                kalan_parti
            )

            parti_bitis = (
                parti_baslangic
                + kullanilacak_parti
                - 1
            )

            plan.append({
                "hammadde_id": ihtiyac["hammadde_id"],
                "hammadde": ihtiyac["hammadde"],
                "depo_kabul_id": lot["id"],
                "tedarikci_lot_no": lot["tedarikci_lot_no"],
                "kabul_tarihi": lot["kabul_tarihi"],
                "parti_baslangic": parti_baslangic,
                "parti_bitis": parti_bitis,
            })

            kalan_parti -= kullanilacak_parti
            parti_baslangic = parti_bitis + 1

            if kalan_parti <= 0:
                break

        if kalan_parti > 0:
            raise ValueError(
                f'{ihtiyac["hammadde"]}: '
                f'{parti_sayisi} parti için uygun tam lot '
                f'aralığı oluşturulamıyor.'
            )

    return plan


def kesin_lot_parti_plani_dogrula(
    conn,
    recete_id,
    parti_sayisi,
    lot_parti_plani
):
    if not lot_parti_plani:
        raise ValueError(
            "Hammadde lot-parti planı boş olamaz."
        )

    ihtiyaclar = recete_ihtiyaclari_getir(
        conn,
        recete_id,
        parti_sayisi
    )

    ihtiyac_map = {
        row["hammadde_id"]: row
        for row in ihtiyaclar
    }

    plan_map = {}

    for row in lot_parti_plani:
        hammadde_id = int(row["hammadde_id"])
        depo_kabul_id = int(row["depo_kabul_id"])
        baslangic = int(row["parti_baslangic"])
        bitis = int(row["parti_bitis"])

        if hammadde_id not in ihtiyac_map:
            raise ValueError(
                f"Reçetede olmayan hammadde planlandı: "
                f"{hammadde_id}"
            )

        if baslangic <= 0:
            raise ValueError(
                "Parti başlangıcı 0'dan büyük olmalıdır."
            )

        if bitis < baslangic:
            raise ValueError(
                "Parti bitişi başlangıçtan küçük olamaz."
            )

        if bitis > parti_sayisi:
            raise ValueError(
                f"Parti aralığı üretim parti sayısını aşıyor: "
                f"{baslangic}-{bitis}"
            )

        lot = conn.execute("""
            SELECT
                hammadde_id,
                kabul_durumu,
                tedarikci_lot_no
            FROM depo_kabul
            WHERE id = ?
        """, (
            depo_kabul_id,
        )).fetchone()

        if lot is None:
            raise ValueError(
                f"Depo kabul lotu bulunamadı: "
                f"{depo_kabul_id}"
            )

        if int(lot["hammadde_id"]) != hammadde_id:
            raise ValueError(
                "Seçilen lot yanlış hammaddeye ait."
            )

        if str(lot["kabul_durumu"]).strip().upper() != "KABUL":
            raise ValueError(
                f'Lot kabul durumunda değil: '
                f'{lot["tedarikci_lot_no"]}'
            )

        plan_map.setdefault(
            hammadde_id,
            []
        ).append({
            "depo_kabul_id": depo_kabul_id,
            "parti_baslangic": baslangic,
            "parti_bitis": bitis,
        })

    for hammadde_id, ihtiyac in ihtiyac_map.items():
        rows = sorted(
            plan_map.get(hammadde_id, []),
            key=lambda x: (
                x["parti_baslangic"],
                x["parti_bitis"],
            )
        )

        if not rows:
            raise ValueError(
                f'{ihtiyac["hammadde"]}: lot planı yok.'
            )

        beklenen = 1

        for row in rows:
            if row["parti_baslangic"] != beklenen:
                raise ValueError(
                    f'{ihtiyac["hammadde"]}: '
                    f'parti aralığında boşluk veya çakışma var. '
                    f'Beklenen başlangıç {beklenen}, '
                    f'girilen {row["parti_baslangic"]}.'
                )

            beklenen = row["parti_bitis"] + 1

        if beklenen != parti_sayisi + 1:
            raise ValueError(
                f'{ihtiyac["hammadde"]}: '
                f'1-{parti_sayisi} parti aralığının tamamı '
                f'lotlarla eşleşmelidir.'
            )

        parti_kg = (
            float(ihtiyac["ihtiyac_kg"])
            / float(parti_sayisi)
        )

        lot_ihtiyaclari = {}

        for row in rows:
            parti_adedi = (
                row["parti_bitis"]
                - row["parti_baslangic"]
                + 1
            )

            miktar = parti_adedi * parti_kg

            lot_ihtiyaclari[
                row["depo_kabul_id"]
            ] = (
                lot_ihtiyaclari.get(
                    row["depo_kabul_id"],
                    0.0
                )
                + miktar
            )

        for depo_kabul_id, miktar in lot_ihtiyaclari.items():
            kalan = lot_kalan_miktar(
                conn,
                depo_kabul_id
            )

            if kalan + 0.000001 < miktar:
                lot = conn.execute("""
                    SELECT tedarikci_lot_no
                    FROM depo_kabul
                    WHERE id = ?
                """, (
                    depo_kabul_id,
                )).fetchone()

                raise ValueError(
                    f'{ihtiyac["hammadde"]} / '
                    f'LOT {lot["tedarikci_lot_no"]}: '
                    f'ihtiyaç {miktar:.3f} kg, '
                    f'mevcut {kalan:.3f} kg.'
                )

    return plan_map, ihtiyac_map


def kesin_lot_parti_tuket(
    conn,
    uretim_id,
    recete_id,
    parti_sayisi,
    lot_parti_plani
):
    plan_map, ihtiyac_map = (
        kesin_lot_parti_plani_dogrula(
            conn,
            recete_id,
            parti_sayisi,
            lot_parti_plani
        )
    )

    for hammadde_id, rows in plan_map.items():
        ihtiyac = ihtiyac_map[hammadde_id]

        parti_kg = (
            float(ihtiyac["ihtiyac_kg"])
            / float(parti_sayisi)
        )

        lot_toplamlari = {}

        for row in rows:
            parti_adedi = (
                row["parti_bitis"]
                - row["parti_baslangic"]
                + 1
            )

            miktar = parti_adedi * parti_kg

            conn.execute("""
                INSERT INTO
                uretim_hammadde_lot_parti_araliklari (
                    uretim_id,
                    hammadde_id,
                    depo_kabul_id,
                    parti_baslangic,
                    parti_bitis,
                    kullanilan_miktar_kg,
                    kayit_tipi
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                uretim_id,
                hammadde_id,
                row["depo_kabul_id"],
                row["parti_baslangic"],
                row["parti_bitis"],
                miktar,
                "KESIN_PARTI_ARALIGI"
            ))

            lot_toplamlari[
                row["depo_kabul_id"]
            ] = (
                lot_toplamlari.get(
                    row["depo_kabul_id"],
                    0.0
                )
                + miktar
            )

        for depo_kabul_id, miktar in lot_toplamlari.items():
            conn.execute("""
                INSERT INTO uretim_hammadde_lotlari (
                    uretim_id,
                    depo_kabul_id,
                    kullanilan_miktar_kg
                )
                VALUES (?, ?, ?)
            """, (
                uretim_id,
                depo_kabul_id,
                miktar
            ))


def uretim_stok_isle(
    conn,
    uretim_id,
    parti_sayisi,
    lot_parti_plani=None
):
    recete = aktif_recete_getir(conn)

    if lot_parti_plani is None:
        fifo_lot_tuket(
            conn,
            uretim_id,
            recete["id"],
            parti_sayisi
        )
    else:
        kesin_lot_parti_tuket(
            conn,
            uretim_id,
            recete["id"],
            parti_sayisi,
            lot_parti_plani
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

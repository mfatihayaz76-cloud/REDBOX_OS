from decimal import Decimal, ROUND_HALF_UP

from database.recipe_approval_engine import (
    recete_icerik_sha256,
)


KG_PRECISION = Decimal("0.001")
MASS_TOLERANCE = Decimal("0.000001")

RECIPE_STATUSES = (
    "TASLAK",
    "INCELEMEDE",
    "ONAYLI",
    "AKTIF",
    "PASIF",
    "ARSIV",
)


def _decimal(value):
    return Decimal(str(value or 0))


def _kg(value):
    return _decimal(value).quantize(
        KG_PRECISION,
        rounding=ROUND_HALF_UP,
    )


def _normalize_status(value):
    if value is None:
        return None

    value = str(value).strip().upper()

    if not value or value in {"TUM", "TÜM"}:
        return None

    if value not in RECIPE_STATUSES:
        raise ValueError(
            f"Geçersiz reçete durumu: {value}"
        )

    return value


def _normalize_limit(value):
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Katalog kayıt sınırı tam sayı olmalıdır."
        ) from exc

    return max(1, min(value, 5000))


def recete_katalogunu_getir(
    conn,
    arama=None,
    durum=None,
    urun_id=None,
    yalniz_aktif_urunler=True,
    limit=500,
):
    durum = _normalize_status(durum)
    limit = _normalize_limit(limit)

    where = []
    params = []

    if yalniz_aktif_urunler:
        where.append("u.aktif = 1")

    if durum:
        where.append("r.durum = ?")
        params.append(durum)

    if urun_id is not None:
        try:
            urun_id = int(urun_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Ürün kimliği tam sayı olmalıdır."
            ) from exc

        if urun_id <= 0:
            raise ValueError(
                "Ürün kimliği pozitif olmalıdır."
            )

        where.append("u.id = ?")
        params.append(urun_id)

    arama = str(arama or "").strip()

    if arama:
        search_value = f"%{arama}%"
        where.append("""
            (
                COALESCE(u.urun_kodu, '') LIKE ?
                OR COALESCE(u.urun_adi, '') LIKE ?
                OR COALESCE(u.kategori, '') LIKE ?
                OR COALESCE(u.barkod, '') LIKE ?
                OR COALESCE(r.recete_kodu, '') LIKE ?
                OR COALESCE(r.ad, '') LIKE ?
                OR COALESCE(r.revizyon_no, '') LIKE ?
                OR COALESCE(r.revizyon_aciklamasi, '') LIKE ?
            )
        """)
        params.extend([search_value] * 8)

    where_sql = (
        " WHERE " + " AND ".join(where)
        if where
        else ""
    )

    rows = conn.execute(
        """
        SELECT
            r.id AS recete_id,
            r.urun_id,
            u.urun_kodu,
            u.urun_adi,
            u.kategori,
            u.barkod,
            u.birim,
            u.raf_omru_gun,
            u.saklama_sicakligi,
            u.aktif AS urun_aktif,
            r.recete_kodu,
            r.ad AS recete_adi,
            r.revizyon_no,
            r.gecerlilik_tarihi,
            r.durum,
            r.aktif AS recete_aktif,
            r.parti_teorik_kg,
            r.proses_suyu_kg,
            r.revizyon_aciklamasi,
            r.icerik_sha256,
            r.olusturan_personel_id,
            r.onaylayan_personel_id,
            r.onay_zamani,
            olusturan.ad_soyad AS olusturan,
            onaylayan.ad_soyad AS onaylayan,
            COUNT(DISTINCT rk.id) AS hammadde_sayisi,
            COALESCE(SUM(rk.miktar_kg), 0)
                AS hammadde_toplami_kg,
            COUNT(DISTINCT ur.id) AS kullanim_sayisi,
            (
                SELECT da.icerik_sha256
                FROM dijital_onaylar da
                WHERE da.kaynak_turu = 'RECETE'
                  AND da.kaynak_id = r.id
                  AND da.onay_turu = 'RECETE_ONAYI'
                  AND da.karar = 'ONAYLANDI'
                ORDER BY da.id DESC
                LIMIT 1
            ) AS onayli_icerik_sha256,
            (
                SELECT COUNT(*)
                FROM dijital_onaylar da
                WHERE da.kaynak_turu = 'RECETE'
                  AND da.kaynak_id = r.id
            ) AS dijital_onay_kaydi
        FROM receteler r
        JOIN urunler u
          ON u.id = r.urun_id
        LEFT JOIN recete_kalemleri rk
          ON rk.recete_id = r.id
        LEFT JOIN uretim_recete ur
          ON ur.recete_id = r.id
        LEFT JOIN personeller olusturan
          ON olusturan.id = r.olusturan_personel_id
        LEFT JOIN personeller onaylayan
          ON onaylayan.id = r.onaylayan_personel_id
        """
        + where_sql
        + """
        GROUP BY
            r.id,
            r.urun_id,
            u.urun_kodu,
            u.urun_adi,
            u.kategori,
            u.barkod,
            u.birim,
            u.raf_omru_gun,
            u.saklama_sicakligi,
            u.aktif,
            r.recete_kodu,
            r.ad,
            r.revizyon_no,
            r.gecerlilik_tarihi,
            r.durum,
            r.aktif,
            r.parti_teorik_kg,
            r.proses_suyu_kg,
            r.revizyon_aciklamasi,
            r.icerik_sha256,
            r.olusturan_personel_id,
            r.onaylayan_personel_id,
            r.onay_zamani,
            olusturan.ad_soyad,
            onaylayan.ad_soyad
        ORDER BY
            u.urun_kodu COLLATE NOCASE,
            CAST(r.revizyon_no AS INTEGER) DESC,
            r.id DESC
        LIMIT ?
        """,
        (*params, limit),
    ).fetchall()

    catalog = []

    for row in rows:
        item = dict(row)

        raw_total = _kg(
            item["hammadde_toplami_kg"]
        )
        water = _kg(
            item["proses_suyu_kg"]
        )
        theoretical = _kg(
            item["parti_teorik_kg"]
        )
        calculated = _kg(
            raw_total + water
        )
        difference = _kg(
            calculated - theoretical
        )

        actual_content_hash = recete_icerik_sha256(
            conn,
            item["recete_id"],
        )
        approved_content_hash = item.get(
            "onayli_icerik_sha256"
        )
        stored_content_hash = item.get(
            "icerik_sha256"
        )

        item.update(
            {
                "hammadde_toplami_kg": float(raw_total),
                "proses_suyu_kg": float(water),
                "parti_teorik_kg": float(theoretical),
                "hesaplanan_parti_kg": float(calculated),
                "kutle_dengesi_farki_kg": float(difference),
                "kutle_dengesi_uyumlu": (
                    abs(
                        raw_total
                        + water
                        - theoretical
                    )
                    <= MASS_TOLERANCE
                ),
                "hesaplanan_icerik_sha256": (
                    actual_content_hash
                ),
                "gecerli_dijital_onay": bool(
                    approved_content_hash
                    and stored_content_hash
                    and approved_content_hash
                    == actual_content_hash
                    and stored_content_hash
                    == actual_content_hash
                ),
                "recete_aktif": bool(
                    item["recete_aktif"]
                ),
                "urun_aktif": bool(
                    item["urun_aktif"]
                ),
            }
        )

        catalog.append(item)

    return catalog


def recete_katalog_ozeti(rows):
    rows = list(rows)

    return {
        "kayit_sayisi": len(rows),
        "urun_sayisi": len(
            {
                row["urun_id"]
                for row in rows
            }
        ),
        "aktif_recete_sayisi": sum(
            1
            for row in rows
            if row["recete_aktif"]
        ),
        "onayli_recete_sayisi": sum(
            1
            for row in rows
            if row["gecerli_dijital_onay"]
        ),
        "kutle_dengesi_hatasi": sum(
            1
            for row in rows
            if not row["kutle_dengesi_uyumlu"]
        ),
    }


def recete_kalemlerini_getir(conn, recete_id):
    try:
        recete_id = int(recete_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Reçete kimliği tam sayı olmalıdır."
        ) from exc

    if recete_id <= 0:
        raise ValueError(
            "Reçete kimliği pozitif olmalıdır."
        )

    return conn.execute(
        """
        SELECT
            rk.id,
            rk.recete_id,
            rk.hammadde_id,
            h.ad AS hammadde,
            rk.miktar_kg
        FROM recete_kalemleri rk
        JOIN hammaddeler h
          ON h.id = rk.hammadde_id
        WHERE rk.recete_id = ?
        ORDER BY
            rk.id
        """,
        (recete_id,),
    ).fetchall()

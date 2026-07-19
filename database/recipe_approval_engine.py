import hashlib
import json
from datetime import datetime

from database.audit_engine import denetim_kaydi_ekle


APPROVABLE_STATUSES = {
    "INCELEMEDE",
    "AKTIF",
}

REJECTABLE_STATUSES = {
    "INCELEMEDE",
}


def _now():
    return datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )


def _user_identity(kullanici):
    kullanici = kullanici or {}

    kullanici_id = kullanici.get(
        "hesap_id",
        kullanici.get("id"),
    )
    personel_id = kullanici.get("personel_id")
    kullanici_adi = str(
        kullanici.get("kullanici_adi") or ""
    ).strip()
    ad_soyad = str(
        kullanici.get("ad_soyad") or ""
    ).strip()

    if (
        kullanici_id is None
        or personel_id is None
        or not kullanici_adi
        or not ad_soyad
    ):
        raise ValueError(
            "Dijital onay için doğrulanmış kullanıcı ve "
            "personel kimliği zorunludur."
        )

    if not bool(kullanici.get("yonetici")):
        raise PermissionError(
            "Reçete dijital onayı yalnızca yönetici "
            "yetkisiyle verilebilir."
        )

    return {
        "kullanici_id": int(kullanici_id),
        "personel_id": int(personel_id),
        "kullanici_adi": kullanici_adi,
        "ad_soyad": ad_soyad,
        "oturum_id": kullanici.get("oturum_id"),
    }


def _recipe_row(conn, recete_id):
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

    row = conn.execute(
        """
        SELECT
            r.id,
            r.urun_id,
            u.urun_kodu,
            r.recete_kodu,
            r.ad AS recete_adi,
            r.revizyon_no,
            r.gecerlilik_tarihi,
            r.durum,
            r.aktif,
            r.parti_teorik_kg,
            r.proses_suyu_kg,
            r.revizyon_aciklamasi,
            r.olusturan_personel_id,
            r.onaylayan_personel_id,
            r.onay_zamani,
            r.icerik_sha256
        FROM receteler r
        JOIN urunler u
          ON u.id = r.urun_id
        WHERE r.id = ?
        LIMIT 1
        """,
        (recete_id,),
    ).fetchone()

    if row is None:
        raise ValueError(
            "Onaylanacak reçete bulunamadı."
        )

    return row


def recete_icerik_sha256(conn, recete_id):
    recipe = _recipe_row(
        conn,
        recete_id,
    )

    materials = conn.execute(
        """
        SELECT
            h.ad AS hammadde,
            rk.miktar_kg
        FROM recete_kalemleri rk
        JOIN hammaddeler h
          ON h.id = rk.hammadde_id
        WHERE rk.recete_id = ?
        ORDER BY
            h.ad COLLATE NOCASE,
            h.id
        """,
        (int(recipe["id"]),),
    ).fetchall()

    if not materials:
        raise ValueError(
            "Kalemsiz reçete dijital işleme alınamaz."
        )

    payload = {
        "urun_kodu": recipe["urun_kodu"],
        "recete_kodu": recipe["recete_kodu"],
        "recete_adi": recipe["recete_adi"],
        "revizyon_no": recipe["revizyon_no"],
        "gecerlilik_tarihi": (
            recipe["gecerlilik_tarihi"]
        ),
        "parti_teorik_kg": round(
            float(recipe["parti_teorik_kg"]),
            6,
        ),
        "proses_suyu_kg": round(
            float(recipe["proses_suyu_kg"]),
            6,
        ),
        "revizyon_aciklamasi": (
            recipe["revizyon_aciklamasi"]
        ),
        "kalemler": [
            {
                "hammadde": row["hammadde"],
                "miktar_kg": round(
                    float(row["miktar_kg"]),
                    6,
                ),
            }
            for row in materials
        ],
    }

    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def _begin_controlled_transaction(conn):
    if conn.in_transaction:
        raise RuntimeError(
            "Reçete onay işlemi mevcut bir transaction "
            "içinde başlatılamaz."
        )

    conn.execute("BEGIN IMMEDIATE")


def receteyi_incelemeye_gonder(
    conn,
    recete_id,
    kullanici,
    aciklama,
):
    identity = _user_identity(kullanici)
    recipe = _recipe_row(conn, recete_id)
    aciklama = str(aciklama or "").strip()

    if recipe["durum"] != "TASLAK":
        raise ValueError(
            "Yalnızca TASLAK reçete incelemeye "
            "gönderilebilir."
        )

    if not aciklama:
        raise ValueError(
            "İncelemeye gönderme açıklaması zorunludur."
        )

    _begin_controlled_transaction(conn)

    try:
        old_data = {
            "durum": recipe["durum"],
            "icerik_sha256": recipe["icerik_sha256"],
        }

        conn.execute(
            """
            UPDATE receteler
            SET
                durum = 'INCELEMEDE',
                aktif = 0,
                onaylayan_personel_id = NULL,
                onay_zamani = NULL
            WHERE id = ?
              AND durum = 'TASLAK'
            """,
            (int(recipe["id"]),),
        )

        content_hash = recete_icerik_sha256(
            conn,
            recipe["id"],
        )

        conn.execute(
            """
            UPDATE receteler
            SET icerik_sha256 = ?
            WHERE id = ?
            """,
            (
                content_hash,
                int(recipe["id"]),
            ),
        )

        denetim_kaydi_ekle(
            conn,
            modul="RECETE",
            islem="DURUM_DEGISIKLIGI",
            kullanici=kullanici,
            kayit_turu="receteler",
            kayit_id=int(recipe["id"]),
            aciklama=aciklama,
            eski_deger=old_data,
            yeni_deger={
                "durum": "INCELEMEDE",
                "icerik_sha256": content_hash,
            },
            oturum_id=identity["oturum_id"],
        )

        conn.commit()

        return {
            "recete_id": int(recipe["id"]),
            "durum": "INCELEMEDE",
            "icerik_sha256": content_hash,
        }

    except Exception:
        conn.rollback()
        raise


def receteyi_dijital_onayla(
    conn,
    recete_id,
    kullanici,
    aciklama,
):
    identity = _user_identity(kullanici)
    recipe = _recipe_row(conn, recete_id)
    aciklama = str(aciklama or "").strip()

    if recipe["durum"] not in APPROVABLE_STATUSES:
        raise ValueError(
            "Yalnızca İNCELEMEDE veya AKTİF reçete "
            "dijital olarak onaylanabilir."
        )

    if not aciklama:
        raise ValueError(
            "Dijital onay açıklaması zorunludur."
        )

    content_hash = recete_icerik_sha256(
        conn,
        recipe["id"],
    )

    duplicate = conn.execute(
        """
        SELECT id
        FROM dijital_onaylar
        WHERE kaynak_turu = 'RECETE'
          AND kaynak_id = ?
          AND onay_turu = 'RECETE_ONAYI'
          AND karar = 'ONAYLANDI'
          AND icerik_sha256 = ?
        LIMIT 1
        """,
        (
            int(recipe["id"]),
            content_hash,
        ),
    ).fetchone()

    if duplicate is not None:
        raise ValueError(
            "Bu reçete içeriği daha önce dijital olarak "
            "onaylanmıştır."
        )

    approval_time = _now()
    new_status = (
        "ONAYLI"
        if recipe["durum"] == "INCELEMEDE"
        else "AKTIF"
    )

    _begin_controlled_transaction(conn)

    try:
        cursor = conn.execute(
            """
            INSERT INTO dijital_onaylar (
                kaynak_turu,
                kaynak_id,
                onay_turu,
                karar,
                kullanici_id,
                personel_id,
                kullanici_adi,
                ad_soyad,
                onay_zamani,
                aciklama,
                icerik_sha256,
                oturum_id
            )
            VALUES (
                'RECETE',
                ?,
                'RECETE_ONAYI',
                'ONAYLANDI',
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                int(recipe["id"]),
                identity["kullanici_id"],
                identity["personel_id"],
                identity["kullanici_adi"],
                identity["ad_soyad"],
                approval_time,
                aciklama,
                content_hash,
                identity["oturum_id"],
            ),
        )

        conn.execute(
            """
            UPDATE receteler
            SET
                durum = ?,
                onaylayan_personel_id = ?,
                onay_zamani = ?,
                icerik_sha256 = ?
            WHERE id = ?
            """,
            (
                new_status,
                identity["personel_id"],
                approval_time,
                content_hash,
                int(recipe["id"]),
            ),
        )

        denetim_kaydi_ekle(
            conn,
            modul="RECETE",
            islem="DURUM_DEGISIKLIGI",
            kullanici=kullanici,
            kayit_turu="receteler",
            kayit_id=int(recipe["id"]),
            aciklama=aciklama,
            eski_deger={
                "durum": recipe["durum"],
                "onaylayan_personel_id": (
                    recipe["onaylayan_personel_id"]
                ),
                "onay_zamani": recipe["onay_zamani"],
                "icerik_sha256": recipe["icerik_sha256"],
            },
            yeni_deger={
                "durum": new_status,
                "onaylayan_personel_id": (
                    identity["personel_id"]
                ),
                "onay_zamani": approval_time,
                "icerik_sha256": content_hash,
                "dijital_onay_id": cursor.lastrowid,
            },
            oturum_id=identity["oturum_id"],
        )

        conn.commit()

        return {
            "recete_id": int(recipe["id"]),
            "dijital_onay_id": cursor.lastrowid,
            "durum": new_status,
            "onay_zamani": approval_time,
            "icerik_sha256": content_hash,
        }

    except Exception:
        conn.rollback()
        raise


def recete_onayini_reddet(
    conn,
    recete_id,
    kullanici,
    aciklama,
):
    identity = _user_identity(kullanici)
    recipe = _recipe_row(conn, recete_id)
    aciklama = str(aciklama or "").strip()

    if recipe["durum"] not in REJECTABLE_STATUSES:
        raise ValueError(
            "Yalnızca İNCELEMEDE reçete reddedilebilir."
        )

    if not aciklama:
        raise ValueError(
            "Ret açıklaması zorunludur."
        )

    content_hash = recete_icerik_sha256(
        conn,
        recipe["id"],
    )
    approval_time = _now()

    _begin_controlled_transaction(conn)

    try:
        cursor = conn.execute(
            """
            INSERT INTO dijital_onaylar (
                kaynak_turu,
                kaynak_id,
                onay_turu,
                karar,
                kullanici_id,
                personel_id,
                kullanici_adi,
                ad_soyad,
                onay_zamani,
                aciklama,
                icerik_sha256,
                oturum_id
            )
            VALUES (
                'RECETE',
                ?,
                'RECETE_ONAYI',
                'REDDEDILDI',
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                int(recipe["id"]),
                identity["kullanici_id"],
                identity["personel_id"],
                identity["kullanici_adi"],
                identity["ad_soyad"],
                approval_time,
                aciklama,
                content_hash,
                identity["oturum_id"],
            ),
        )

        conn.execute(
            """
            UPDATE receteler
            SET
                durum = 'TASLAK',
                aktif = 0,
                onaylayan_personel_id = NULL,
                onay_zamani = NULL,
                icerik_sha256 = ?
            WHERE id = ?
            """,
            (
                content_hash,
                int(recipe["id"]),
            ),
        )

        denetim_kaydi_ekle(
            conn,
            modul="RECETE",
            islem="DURUM_DEGISIKLIGI",
            kullanici=kullanici,
            kayit_turu="receteler",
            kayit_id=int(recipe["id"]),
            aciklama=aciklama,
            eski_deger={
                "durum": recipe["durum"],
                "icerik_sha256": recipe["icerik_sha256"],
            },
            yeni_deger={
                "durum": "TASLAK",
                "icerik_sha256": content_hash,
                "dijital_onay_id": cursor.lastrowid,
                "karar": "REDDEDILDI",
            },
            oturum_id=identity["oturum_id"],
        )

        conn.commit()

        return {
            "recete_id": int(recipe["id"]),
            "dijital_onay_id": cursor.lastrowid,
            "durum": "TASLAK",
            "karar": "REDDEDILDI",
            "icerik_sha256": content_hash,
        }

    except Exception:
        conn.rollback()
        raise

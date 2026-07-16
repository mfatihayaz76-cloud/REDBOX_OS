import json
import uuid
from datetime import datetime


ALLOWED_ACTIONS = {
    "GIRIS_BASARILI",
    "GIRIS_BASARISIZ",
    "OLUSTURMA",
    "GUNCELLEME",
    "SILME",
    "AKTIFLIK_DEGISIKLIGI",
    "YEDEKLEME",
    "GERI_YUKLEME",
    "PDF_OLUSTURMA",
    "YETKI_DEGISIKLIGI",
    "SAYIM_DUZELTME",
    "DURUM_DEGISIKLIGI",
}


def yeni_oturum_id():
    return uuid.uuid4().hex


def _json_value(value):
    if value is None:
        return None

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def denetim_kaydi_ekle(
    conn,
    modul,
    islem,
    kullanici=None,
    kayit_turu=None,
    kayit_id=None,
    aciklama=None,
    eski_deger=None,
    yeni_deger=None,
    oturum_id=None,
    olay_zamani=None,
):
    modul = str(modul).strip().upper()
    islem = str(islem).strip().upper()

    if not modul:
        raise ValueError("Denetim modülü boş olamaz.")

    if islem not in ALLOWED_ACTIONS:
        raise ValueError(
            f"Geçersiz denetim işlemi: {islem}"
        )

    kullanici = kullanici or {}

    cursor = conn.execute(
        """
        INSERT INTO denetim_kayitlari (
            olay_zamani,
            kullanici_id,
            personel_id,
            kullanici_adi,
            ad_soyad,
            modul,
            islem,
            kayit_turu,
            kayit_id,
            aciklama,
            eski_deger_json,
            yeni_deger_json,
            oturum_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            olay_zamani or datetime.now().strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
            kullanici.get(
                "hesap_id",
                kullanici.get("id"),
            ),
            kullanici.get("personel_id"),
            kullanici.get("kullanici_adi"),
            kullanici.get("ad_soyad"),
            modul,
            islem,
            kayit_turu,
            kayit_id,
            aciklama,
            _json_value(eski_deger),
            _json_value(yeni_deger),
            oturum_id,
        ),
    )

    return cursor.lastrowid


def denetim_kayitlarini_getir(
    conn,
    modul=None,
    islem=None,
    kullanici_adi=None,
    limit=500,
):
    where = []
    params = []

    if modul:
        where.append("modul = ?")
        params.append(str(modul).strip().upper())

    if islem:
        where.append("islem = ?")
        params.append(str(islem).strip().upper())

    if kullanici_adi:
        where.append("kullanici_adi = ?")
        params.append(str(kullanici_adi).strip())

    limit = max(1, min(int(limit), 5000))
    where_sql = (
        " WHERE " + " AND ".join(where)
        if where
        else ""
    )

    return conn.execute(
        """
        SELECT
            id,
            olay_zamani,
            kullanici_id,
            personel_id,
            kullanici_adi,
            ad_soyad,
            modul,
            islem,
            kayit_turu,
            kayit_id,
            aciklama,
            eski_deger_json,
            yeni_deger_json,
            oturum_id
        FROM denetim_kayitlari
        """
        + where_sql
        + " ORDER BY id DESC LIMIT ?",
        (*params, limit),
    ).fetchall()

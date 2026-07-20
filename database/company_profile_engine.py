from datetime import datetime

from database.audit_engine import denetim_kaydi_ekle


def _text(value, field_name, required=False):
    normalized = " ".join(
        str(value or "").strip().split()
    )

    if required and not normalized:
        raise ValueError(
            field_name + " boş olamaz."
        )

    return normalized or None


def _email(value):
    normalized = _text(value, "E-posta")

    if normalized is None:
        return None

    if (
        normalized.count("@") != 1
        or "." not in normalized.split("@", 1)[1]
    ):
        raise ValueError("Geçerli bir e-posta girin.")

    return normalized.casefold()


def _company_payload(firma):
    if not isinstance(firma, dict):
        raise ValueError(
            "Firma bilgileri sözlük olmalıdır."
        )

    return {
        "ticari_unvan": _text(
            firma.get("ticari_unvan"),
            "Ticari unvan",
            required=True,
        ),
        "kisa_ad": _text(
            firma.get("kisa_ad"),
            "Firma kısa adı",
            required=True,
        ),
        "vergi_dairesi": _text(
            firma.get("vergi_dairesi"),
            "Vergi dairesi",
        ),
        "vergi_no": _text(
            firma.get("vergi_no"),
            "Vergi numarası",
        ),
        "ulke": _text(
            firma.get("ulke") or "Türkiye",
            "Ülke",
            required=True,
        ),
        "il": _text(firma.get("il"), "İl"),
        "ilce": _text(firma.get("ilce"), "İlçe"),
        "adres": _text(
            firma.get("adres"),
            "Açık adres",
        ),
        "telefon": _text(
            firma.get("telefon"),
            "Telefon",
        ),
        "eposta": _email(
            firma.get("eposta")
        ),
    }


def firma_profilini_getir(conn):
    row = conn.execute(
        """
        SELECT
            id,
            ticari_unvan,
            kisa_ad,
            vergi_dairesi,
            vergi_no,
            ulke,
            il,
            ilce,
            adres,
            telefon,
            eposta,
            aktif,
            kayit_zamani,
            guncelleme_zamani
        FROM firma_profili
        WHERE id = 1
        """
    ).fetchone()

    if row is None:
        return None

    keys = (
        "id",
        "ticari_unvan",
        "kisa_ad",
        "vergi_dairesi",
        "vergi_no",
        "ulke",
        "il",
        "ilce",
        "adres",
        "telefon",
        "eposta",
        "aktif",
        "kayit_zamani",
        "guncelleme_zamani",
    )

    return dict(zip(keys, row))


def legacy_firma_profilini_olustur(
    conn,
    firma,
    kullanici=None,
    oturum_id=None,
    simdi=None,
):
    if conn.in_transaction:
        raise RuntimeError(
            "Firma profili işlemi temiz transaction gerektirir."
        )

    payload = _company_payload(firma)

    active_accounts = conn.execute(
        """
        SELECT COUNT(*)
        FROM kullanici_hesaplari
        WHERE aktif = 1
        """
    ).fetchone()[0]

    if active_accounts < 1:
        raise RuntimeError(
            "Legacy firma profili yalnız mevcut kurulumda oluşturulabilir."
        )

    existing = firma_profilini_getir(conn)

    if existing is not None:
        raise RuntimeError(
            "Firma profili zaten mevcut."
        )

    timestamp = (
        simdi.isoformat()
        if isinstance(simdi, datetime)
        else str(simdi).strip()
        if simdi is not None
        else datetime.now().astimezone().isoformat()
    )

    if not timestamp:
        raise ValueError("Kayıt zamanı boş olamaz.")

    try:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute(
            """
            INSERT INTO firma_profili (
                id,
                ticari_unvan,
                kisa_ad,
                vergi_dairesi,
                vergi_no,
                ulke,
                il,
                ilce,
                adres,
                telefon,
                eposta,
                aktif,
                kayit_zamani,
                guncelleme_zamani
            )
            VALUES (
                1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                1, ?, ?
            )
            """,
            (
                payload["ticari_unvan"],
                payload["kisa_ad"],
                payload["vergi_dairesi"],
                payload["vergi_no"],
                payload["ulke"],
                payload["il"],
                payload["ilce"],
                payload["adres"],
                payload["telefon"],
                payload["eposta"],
                timestamp,
                timestamp,
            ),
        )

        denetim_kaydi_ekle(
            conn,
            modul="SISTEM",
            islem="OLUSTURMA",
            kullanici=kullanici,
            kayit_turu="firma_profili_legacy",
            kayit_id=1,
            aciklama=(
                "Mevcut kurulumun firma profili "
                "kullanıcı onayıyla tamamlandı."
            ),
            yeni_deger={
                key: value
                for key, value in payload.items()
                if key not in {
                    "vergi_no",
                    "telefon",
                    "eposta",
                    "adres",
                }
            },
            oturum_id=oturum_id,
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return firma_profilini_getir(conn)

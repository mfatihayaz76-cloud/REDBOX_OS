from datetime import datetime

from database.audit_engine import denetim_kaydi_ekle


QUALITY_SOURCES = {
    "DEPO_KABUL",
    "URETIM",
    "PAKETLEME",
    "SEVKIYAT",
    "TEMIZLIK",
    "MUSTERI_SIKAYETI",
    "TEDARIKCI",
    "DIGER",
}

SEVERITY_LEVELS = {
    "DUSUK",
    "ORTA",
    "YUKSEK",
    "KRITIK",
}

NONCONFORMITY_STATUSES = {
    "ACIK",
    "INCELEMEDE",
    "AKSIYONDA",
    "DOGRULAMADA",
    "KAPALI",
    "IPTAL",
}

CAPA_TYPES = {
    "DUZELTME",
    "DUZELTICI",
    "ONLEYICI",
}

CAPA_STATUSES = {
    "ACIK",
    "DEVAM_EDIYOR",
    "TAMAMLANDI",
    "IPTAL",
}

EFFECTIVENESS_STATUSES = {
    "BEKLIYOR",
    "ETKILI",
    "ETKISIZ",
}

NONCONFORMITY_TRANSITIONS = {
    "ACIK": {
        "INCELEMEDE",
        "AKSIYONDA",
        "IPTAL",
    },
    "INCELEMEDE": {
        "AKSIYONDA",
        "DOGRULAMADA",
        "IPTAL",
    },
    "AKSIYONDA": {
        "DOGRULAMADA",
        "IPTAL",
    },
    "DOGRULAMADA": {
        "AKSIYONDA",
        "KAPALI",
        "IPTAL",
    },
    "KAPALI": set(),
    "IPTAL": set(),
}

CAPA_TRANSITIONS = {
    "ACIK": {
        "DEVAM_EDIYOR",
        "TAMAMLANDI",
        "IPTAL",
    },
    "DEVAM_EDIYOR": {
        "TAMAMLANDI",
        "IPTAL",
    },
    "TAMAMLANDI": set(),
    "IPTAL": set(),
}


def _normalize(value):
    return str(value or "").strip().upper()


def _required_text(value, field_name):
    text = str(value or "").strip()

    if not text:
        raise ValueError(
            f"{field_name} boş bırakılamaz."
        )

    return text


def _validate_date(value, field_name, required=True):
    text = str(value or "").strip()

    if not text and not required:
        return None

    if not text:
        raise ValueError(
            f"{field_name} boş bırakılamaz."
        )

    try:
        datetime.strptime(
            text,
            "%d.%m.%Y",
        )
    except ValueError as exc:
        raise ValueError(
            f"{field_name} GG.AA.YYYY formatında olmalıdır."
        ) from exc

    return text


def _now():
    return datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )


def uygunsuzluk_kayit_no_uret(
    conn,
    kayit_tarihi,
):
    tarih = _validate_date(
        kayit_tarihi,
        "Kayıt tarihi",
    )
    year = datetime.strptime(
        tarih,
        "%d.%m.%Y",
    ).year
    prefix = f"UYG-{year}-"

    rows = conn.execute("""
        SELECT kayit_no
        FROM kalite_uygunsuzluklari
        WHERE kayit_no LIKE ?
        ORDER BY kayit_no DESC
        LIMIT 1
    """, (
        f"{prefix}%",
    )).fetchall()

    sequence = 1

    if rows:
        try:
            sequence = int(
                rows[0]["kayit_no"].split("-")[-1]
            ) + 1
        except (ValueError, IndexError, TypeError):
            raise RuntimeError(
                "Mevcut uygunsuzluk kayıt numarası "
                "sözleşmeye uygun değil."
            )

    return f"{prefix}{sequence:04d}"


def uygunsuzluk_olustur(
    conn,
    *,
    kayit_tarihi,
    tespit_tarihi,
    kaynak_turu,
    kategori,
    baslik,
    aciklama,
    onem_derecesi,
    bildiren_personel_id,
    sorumlu_personel_id=None,
    hedef_tarih=None,
    anlik_aksiyon=None,
    depo_kabul_id=None,
    uretim_id=None,
    paketleme_id=None,
    sevkiyat_id=None,
    tedarikci_id=None,
    musteri_id=None,
    kullanici=None,
):
    kayit_tarihi = _validate_date(
        kayit_tarihi,
        "Kayıt tarihi",
    )
    tespit_tarihi = _validate_date(
        tespit_tarihi,
        "Tespit tarihi",
    )
    hedef_tarih = _validate_date(
        hedef_tarih,
        "Hedef tarih",
        required=False,
    )

    kaynak_turu = _normalize(kaynak_turu)
    onem_derecesi = _normalize(onem_derecesi)

    if kaynak_turu not in QUALITY_SOURCES:
        raise ValueError(
            "Geçersiz uygunsuzluk kaynak türü."
        )

    if onem_derecesi not in SEVERITY_LEVELS:
        raise ValueError(
            "Geçersiz önem derecesi."
        )

    kategori = _required_text(
        kategori,
        "Kategori",
    )
    baslik = _required_text(
        baslik,
        "Başlık",
    )
    aciklama = _required_text(
        aciklama,
        "Açıklama",
    )

    if bildiren_personel_id is None:
        raise ValueError(
            "Bildiren personel zorunludur."
        )

    kayit_no = uygunsuzluk_kayit_no_uret(
        conn,
        kayit_tarihi,
    )
    now = _now()

    cursor = conn.execute("""
        INSERT INTO kalite_uygunsuzluklari (
            kayit_no,
            kayit_tarihi,
            tespit_tarihi,
            kaynak_turu,
            kategori,
            baslik,
            aciklama,
            onem_derecesi,
            durum,
            depo_kabul_id,
            uretim_id,
            paketleme_id,
            sevkiyat_id,
            tedarikci_id,
            musteri_id,
            bildiren_personel_id,
            sorumlu_personel_id,
            hedef_tarih,
            anlik_aksiyon,
            kayit_zamani,
            guncelleme_zamani
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, 'ACIK',
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, (
        kayit_no,
        kayit_tarihi,
        tespit_tarihi,
        kaynak_turu,
        kategori,
        baslik,
        aciklama,
        onem_derecesi,
        depo_kabul_id,
        uretim_id,
        paketleme_id,
        sevkiyat_id,
        tedarikci_id,
        musteri_id,
        bildiren_personel_id,
        sorumlu_personel_id,
        hedef_tarih,
        str(anlik_aksiyon or "").strip() or None,
        now,
        now,
    ))

    uygunsuzluk_id = cursor.lastrowid

    denetim_kaydi_ekle(
        conn,
        modul="KALITE",
        islem="OLUSTURMA",
        kullanici=kullanici,
        kayit_turu="kalite_uygunsuzluklari",
        kayit_id=uygunsuzluk_id,
        aciklama=(
            f"{kayit_no} numaralı uygunsuzluk "
            "kaydı oluşturuldu."
        ),
        yeni_deger={
            "kayit_no": kayit_no,
            "kaynak_turu": kaynak_turu,
            "kategori": kategori,
            "baslik": baslik,
            "onem_derecesi": onem_derecesi,
            "durum": "ACIK",
            "bildiren_personel_id": (
                bildiren_personel_id
            ),
            "sorumlu_personel_id": (
                sorumlu_personel_id
            ),
            "hedef_tarih": hedef_tarih,
        },
        oturum_id=(kullanici or {}).get(
            "oturum_id"
        ),
    )

    return uygunsuzluk_id, kayit_no


def capa_faaliyeti_ekle(
    conn,
    *,
    uygunsuzluk_id,
    faaliyet_turu,
    aciklama,
    sorumlu_personel_id,
    hedef_tarih,
    kullanici=None,
):
    faaliyet_turu = _normalize(
        faaliyet_turu
    )

    if faaliyet_turu not in CAPA_TYPES:
        raise ValueError(
            "Geçersiz CAPA faaliyet türü."
        )

    aciklama = _required_text(
        aciklama,
        "Faaliyet açıklaması",
    )
    hedef_tarih = _validate_date(
        hedef_tarih,
        "Hedef tarih",
    )

    uygunsuzluk = conn.execute("""
        SELECT
            id,
            kayit_no,
            durum
        FROM kalite_uygunsuzluklari
        WHERE id = ?
    """, (
        uygunsuzluk_id,
    )).fetchone()

    if uygunsuzluk is None:
        raise ValueError(
            "Bağlı uygunsuzluk kaydı bulunamadı."
        )

    if uygunsuzluk["durum"] in {
        "KAPALI",
        "IPTAL",
    }:
        raise ValueError(
            "Kapalı veya iptal edilmiş uygunsuzluğa "
            "CAPA faaliyeti eklenemez."
        )

    now = _now()

    cursor = conn.execute("""
        INSERT INTO kalite_capa_faaliyetleri (
            uygunsuzluk_id,
            faaliyet_turu,
            aciklama,
            sorumlu_personel_id,
            hedef_tarih,
            durum,
            etkinlik_durumu,
            kayit_zamani,
            guncelleme_zamani
        )
        VALUES (?, ?, ?, ?, ?, 'ACIK', 'BEKLIYOR', ?, ?)
    """, (
        uygunsuzluk_id,
        faaliyet_turu,
        aciklama,
        sorumlu_personel_id,
        hedef_tarih,
        now,
        now,
    ))

    capa_id = cursor.lastrowid

    conn.execute("""
        UPDATE kalite_uygunsuzluklari
        SET
            durum = CASE
                WHEN durum IN ('ACIK', 'INCELEMEDE')
                THEN 'AKSIYONDA'
                ELSE durum
            END,
            guncelleme_zamani = ?
        WHERE id = ?
    """, (
        now,
        uygunsuzluk_id,
    ))

    denetim_kaydi_ekle(
        conn,
        modul="KALITE",
        islem="OLUSTURMA",
        kullanici=kullanici,
        kayit_turu="kalite_capa_faaliyetleri",
        kayit_id=capa_id,
        aciklama=(
            f'{uygunsuzluk["kayit_no"]} için '
            "CAPA faaliyeti oluşturuldu."
        ),
        yeni_deger={
            "uygunsuzluk_id": uygunsuzluk_id,
            "faaliyet_turu": faaliyet_turu,
            "sorumlu_personel_id": (
                sorumlu_personel_id
            ),
            "hedef_tarih": hedef_tarih,
            "durum": "ACIK",
        },
        oturum_id=(kullanici or {}).get(
            "oturum_id"
        ),
    )

    return capa_id


def capa_durum_guncelle(
    conn,
    *,
    capa_id,
    yeni_durum,
    tamamlanma_tarihi=None,
    tamamlanma_aciklamasi=None,
    kullanici=None,
):
    yeni_durum = _normalize(yeni_durum)

    if yeni_durum not in CAPA_STATUSES:
        raise ValueError(
            "Geçersiz CAPA durumu."
        )

    row = conn.execute("""
        SELECT
            id,
            uygunsuzluk_id,
            durum,
            faaliyet_turu
        FROM kalite_capa_faaliyetleri
        WHERE id = ?
    """, (
        capa_id,
    )).fetchone()

    if row is None:
        raise ValueError(
            "CAPA faaliyeti bulunamadı."
        )

    mevcut_durum = row["durum"]

    if yeni_durum not in CAPA_TRANSITIONS[
        mevcut_durum
    ]:
        raise ValueError(
            f"Geçersiz CAPA durum geçişi: "
            f"{mevcut_durum} -> {yeni_durum}"
        )

    if yeni_durum == "TAMAMLANDI":
        tamamlanma_tarihi = _validate_date(
            tamamlanma_tarihi,
            "Tamamlanma tarihi",
        )
        tamamlanma_aciklamasi = _required_text(
            tamamlanma_aciklamasi,
            "Tamamlanma açıklaması",
        )
    else:
        tamamlanma_tarihi = None
        tamamlanma_aciklamasi = None

    now = _now()

    conn.execute("""
        UPDATE kalite_capa_faaliyetleri
        SET
            durum = ?,
            tamamlanma_tarihi = ?,
            tamamlanma_aciklamasi = ?,
            guncelleme_zamani = ?
        WHERE id = ?
    """, (
        yeni_durum,
        tamamlanma_tarihi,
        tamamlanma_aciklamasi,
        now,
        capa_id,
    ))

    denetim_kaydi_ekle(
        conn,
        modul="KALITE",
        islem="DURUM_DEGISIKLIGI",
        kullanici=kullanici,
        kayit_turu="kalite_capa_faaliyetleri",
        kayit_id=capa_id,
        aciklama="CAPA faaliyet durumu değiştirildi.",
        eski_deger={
            "durum": mevcut_durum,
        },
        yeni_deger={
            "durum": yeni_durum,
            "tamamlanma_tarihi": (
                tamamlanma_tarihi
            ),
        },
        oturum_id=(kullanici or {}).get(
            "oturum_id"
        ),
    )


def capa_etkinlik_dogrula(
    conn,
    *,
    capa_id,
    etkinlik_durumu,
    etkinlik_aciklamasi,
    dogrulayan_personel_id,
    dogrulama_tarihi,
    kullanici=None,
):
    etkinlik_durumu = _normalize(
        etkinlik_durumu
    )

    if etkinlik_durumu not in {
        "ETKILI",
        "ETKISIZ",
    }:
        raise ValueError(
            "Etkinlik sonucu ETKILI veya ETKISIZ olmalıdır."
        )

    etkinlik_aciklamasi = _required_text(
        etkinlik_aciklamasi,
        "Etkinlik açıklaması",
    )
    dogrulama_tarihi = _validate_date(
        dogrulama_tarihi,
        "Doğrulama tarihi",
    )

    row = conn.execute("""
        SELECT
            id,
            durum,
            etkinlik_durumu
        FROM kalite_capa_faaliyetleri
        WHERE id = ?
    """, (
        capa_id,
    )).fetchone()

    if row is None:
        raise ValueError(
            "CAPA faaliyeti bulunamadı."
        )

    if row["durum"] != "TAMAMLANDI":
        raise ValueError(
            "Yalnız tamamlanmış CAPA faaliyetinin "
            "etkinliği doğrulanabilir."
        )

    old_effectiveness = row["etkinlik_durumu"]
    now = _now()

    conn.execute("""
        UPDATE kalite_capa_faaliyetleri
        SET
            etkinlik_durumu = ?,
            etkinlik_aciklamasi = ?,
            dogrulayan_personel_id = ?,
            dogrulama_tarihi = ?,
            guncelleme_zamani = ?
        WHERE id = ?
    """, (
        etkinlik_durumu,
        etkinlik_aciklamasi,
        dogrulayan_personel_id,
        dogrulama_tarihi,
        now,
        capa_id,
    ))

    if etkinlik_durumu == "ETKISIZ":
        conn.execute("""
            UPDATE kalite_uygunsuzluklari
            SET
                durum = 'AKSIYONDA',
                guncelleme_zamani = ?
            WHERE id = (
                SELECT uygunsuzluk_id
                FROM kalite_capa_faaliyetleri
                WHERE id = ?
            )
        """, (
            now,
            capa_id,
        ))

    denetim_kaydi_ekle(
        conn,
        modul="KALITE",
        islem="DURUM_DEGISIKLIGI",
        kullanici=kullanici,
        kayit_turu="kalite_capa_faaliyetleri",
        kayit_id=capa_id,
        aciklama="CAPA etkinlik doğrulaması kaydedildi.",
        eski_deger={
            "etkinlik_durumu": old_effectiveness,
        },
        yeni_deger={
            "etkinlik_durumu": etkinlik_durumu,
            "dogrulayan_personel_id": (
                dogrulayan_personel_id
            ),
            "dogrulama_tarihi": dogrulama_tarihi,
        },
        oturum_id=(kullanici or {}).get(
            "oturum_id"
        ),
    )


def uygunsuzluk_durum_guncelle(
    conn,
    *,
    uygunsuzluk_id,
    yeni_durum,
    kok_neden=None,
    kapanis_aciklamasi=None,
    kapatma_tarihi=None,
    kullanici=None,
):
    yeni_durum = _normalize(yeni_durum)

    if yeni_durum not in NONCONFORMITY_STATUSES:
        raise ValueError(
            "Geçersiz uygunsuzluk durumu."
        )

    row = conn.execute("""
        SELECT
            id,
            kayit_no,
            durum,
            onem_derecesi,
            kok_neden
        FROM kalite_uygunsuzluklari
        WHERE id = ?
    """, (
        uygunsuzluk_id,
    )).fetchone()

    if row is None:
        raise ValueError(
            "Uygunsuzluk kaydı bulunamadı."
        )

    mevcut_durum = row["durum"]

    if yeni_durum not in NONCONFORMITY_TRANSITIONS[
        mevcut_durum
    ]:
        raise ValueError(
            f"Geçersiz uygunsuzluk durum geçişi: "
            f"{mevcut_durum} -> {yeni_durum}"
        )

    kok_neden_value = (
        str(kok_neden or row["kok_neden"] or "")
        .strip()
        or None
    )
    kapanis_value = None
    kapatma_value = None

    if yeni_durum == "KAPALI":
        kok_neden_value = _required_text(
            kok_neden_value,
            "Kök neden",
        )
        kapanis_value = _required_text(
            kapanis_aciklamasi,
            "Kapanış açıklaması",
        )
        kapatma_value = _validate_date(
            kapatma_tarihi,
            "Kapatma tarihi",
        )

        open_capa = conn.execute("""
            SELECT COUNT(*)
            FROM kalite_capa_faaliyetleri
            WHERE uygunsuzluk_id = ?
              AND durum IN (
                  'ACIK',
                  'DEVAM_EDIYOR'
              )
        """, (
            uygunsuzluk_id,
        )).fetchone()[0]

        if open_capa:
            raise ValueError(
                "Açık CAPA faaliyeti varken "
                "uygunsuzluk kapatılamaz."
            )

        capa_summary = conn.execute("""
            SELECT
                COUNT(*) AS toplam,
                SUM(
                    CASE
                        WHEN etkinlik_durumu = 'ETKILI'
                        THEN 1
                        ELSE 0
                    END
                ) AS etkili
            FROM kalite_capa_faaliyetleri
            WHERE uygunsuzluk_id = ?
              AND durum != 'IPTAL'
        """, (
            uygunsuzluk_id,
        )).fetchone()

        total_capa = int(
            capa_summary["toplam"] or 0
        )
        effective_capa = int(
            capa_summary["etkili"] or 0
        )

        if (
            row["onem_derecesi"] == "KRITIK"
            and total_capa == 0
        ):
            raise ValueError(
                "Kritik uygunsuzluk CAPA faaliyeti "
                "olmadan kapatılamaz."
            )

        if total_capa != effective_capa:
            raise ValueError(
                "Tüm CAPA faaliyetleri etkili olarak "
                "doğrulanmadan uygunsuzluk kapatılamaz."
            )

    now = _now()

    conn.execute("""
        UPDATE kalite_uygunsuzluklari
        SET
            durum = ?,
            kok_neden = ?,
            kapatma_tarihi = ?,
            kapanis_aciklamasi = ?,
            guncelleme_zamani = ?
        WHERE id = ?
    """, (
        yeni_durum,
        kok_neden_value,
        kapatma_value,
        kapanis_value,
        now,
        uygunsuzluk_id,
    ))

    denetim_kaydi_ekle(
        conn,
        modul="KALITE",
        islem="DURUM_DEGISIKLIGI",
        kullanici=kullanici,
        kayit_turu="kalite_uygunsuzluklari",
        kayit_id=uygunsuzluk_id,
        aciklama=(
            f'{row["kayit_no"]} uygunsuzluk '
            "durumu değiştirildi."
        ),
        eski_deger={
            "durum": mevcut_durum,
        },
        yeni_deger={
            "durum": yeni_durum,
            "kapatma_tarihi": kapatma_value,
        },
        oturum_id=(kullanici or {}).get(
            "oturum_id"
        ),
    )


def kalite_ozeti(conn):
    return conn.execute("""
        SELECT
            COUNT(*) AS toplam,
            SUM(
                CASE
                    WHEN durum NOT IN ('KAPALI', 'IPTAL')
                    THEN 1
                    ELSE 0
                END
            ) AS acik,
            SUM(
                CASE
                    WHEN onem_derecesi = 'KRITIK'
                     AND durum NOT IN ('KAPALI', 'IPTAL')
                    THEN 1
                    ELSE 0
                END
            ) AS kritik,
            SUM(
                CASE
                    WHEN hedef_tarih IS NOT NULL
                     AND durum NOT IN ('KAPALI', 'IPTAL')
                     AND substr(hedef_tarih, 7, 4)
                         || substr(hedef_tarih, 4, 2)
                         || substr(hedef_tarih, 1, 2)
                         < strftime('%Y%m%d', 'now', 'localtime')
                    THEN 1
                    ELSE 0
                END
            ) AS geciken
        FROM kalite_uygunsuzluklari
    """).fetchone()


def uygunsuzluklari_getir(
    conn,
    *,
    arama=None,
    durum=None,
    onem_derecesi=None,
    limit=500,
):
    where = []
    params = []

    if durum:
        where.append("ku.durum = ?")
        params.append(_normalize(durum))

    if onem_derecesi:
        where.append("ku.onem_derecesi = ?")
        params.append(
            _normalize(onem_derecesi)
        )

    if arama:
        search = f"%{str(arama).strip()}%"
        where.append("""
            (
                ku.kayit_no LIKE ?
                OR ku.baslik LIKE ?
                OR ku.kategori LIKE ?
                OR ku.aciklama LIKE ?
                OR ku.kaynak_turu LIKE ?
                OR COALESCE(p.ad_soyad, '') LIKE ?
            )
        """)
        params.extend([search] * 6)

    where_sql = (
        " WHERE " + " AND ".join(where)
        if where
        else ""
    )
    limit = max(1, min(int(limit), 5000))

    return conn.execute(
        """
        SELECT
            ku.*,
            p.ad_soyad AS sorumlu_personel,
            bp.ad_soyad AS bildiren_personel,
            (
                SELECT COUNT(*)
                FROM kalite_capa_faaliyetleri kcf
                WHERE kcf.uygunsuzluk_id = ku.id
                  AND kcf.durum NOT IN (
                      'TAMAMLANDI',
                      'IPTAL'
                  )
            ) AS acik_capa
        FROM kalite_uygunsuzluklari ku
        LEFT JOIN personeller p
          ON p.id = ku.sorumlu_personel_id
        LEFT JOIN personeller bp
          ON bp.id = ku.bildiren_personel_id
        """
        + where_sql
        + " ORDER BY ku.id DESC LIMIT ?",
        (*params, limit),
    ).fetchall()


def capa_faaliyetlerini_getir(
    conn,
    uygunsuzluk_id,
):
    return conn.execute("""
        SELECT
            kcf.*,
            p.ad_soyad AS sorumlu_personel,
            dp.ad_soyad AS dogrulayan_personel
        FROM kalite_capa_faaliyetleri kcf
        JOIN personeller p
          ON p.id = kcf.sorumlu_personel_id
        LEFT JOIN personeller dp
          ON dp.id = kcf.dogrulayan_personel_id
        WHERE kcf.uygunsuzluk_id = ?
        ORDER BY kcf.id
    """, (
        uygunsuzluk_id,
    )).fetchall()

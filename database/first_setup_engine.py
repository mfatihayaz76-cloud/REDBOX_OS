import hashlib
import os
import re
from datetime import datetime

from database.audit_engine import denetim_kaydi_ekle


PBKDF2_ITERATIONS = 600_000

KULLANIM_MODLARI = {
    "GERCEK",
    "DEMO",
}

TESIS_TURLERI = {
    "URETIM",
    "DEPO",
    "MERKEZ",
    "DIGER",
}

ILK_YONETICI_YETKILERI = (
    "DEPO_KABUL",
    "PAKETLEME",
    "SEVKIYAT",
    "TEMIZLIK",
    "URETIM",
    "STOK",
    "IZLENEBILIRLIK",
    "KALITE",
    "PERSONEL",
    "SISTEM",
)

KULLANICI_ADI_PATTERN = re.compile(
    r"^[a-zA-Z0-9._-]{3,50}$"
)

TESIS_KODU_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9._-]{1,49}$"
)


def _text(value):
    if value is None:
        return ""

    return " ".join(str(value).strip().split())


def _required(data, field, label):
    value = _text(data.get(field))

    if not value:
        raise ValueError(f"{label} zorunludur.")

    return value


def parola_hash_olustur(
    parola,
    tuz,
    iterasyon=PBKDF2_ITERATIONS,
):
    return hashlib.pbkdf2_hmac(
        "sha256",
        parola.encode("utf-8"),
        bytes.fromhex(tuz),
        iterasyon,
    ).hex()


def ilk_kurulum_gerekli_mi(conn):
    completed = conn.execute("""
        SELECT tamamlandi
        FROM ilk_kurulum_durumu
        WHERE id = 1
    """).fetchone()

    if completed is not None and int(completed[0]) == 1:
        return False

    account_count = conn.execute("""
        SELECT COUNT(*)
        FROM kullanici_hesaplari
        WHERE aktif = 1
    """).fetchone()[0]

    return account_count == 0


def uygulama_kimligini_getir(conn):
    setup = conn.execute("""
        SELECT
            fp.ticari_unvan,
            fp.kisa_ad,
            tp.tesis_kodu,
            tp.tesis_adi,
            kd.kullanim_modu
        FROM ilk_kurulum_durumu AS kd
        JOIN firma_profili AS fp
          ON fp.id = kd.firma_id
        JOIN tesis_profilleri AS tp
          ON tp.id = kd.tesis_id
        WHERE kd.id = 1
          AND kd.tamamlandi = 1
        LIMIT 1
    """).fetchone()

    if setup is not None:
        return {
            "ticari_unvan": setup[0],
            "firma_kisa_ad": setup[1],
            "tesis_kodu": setup[2],
            "tesis_adi": setup[3],
            "kullanim_modu": setup[4],
            "kurulum_tamamlandi": True,
            "legacy_kimlik": False,
        }

    active_accounts = conn.execute("""
        SELECT COUNT(*)
        FROM kullanici_hesaplari
        WHERE aktif = 1
    """).fetchone()[0]

    if active_accounts:
        redbox_product = conn.execute("""
            SELECT 1
            FROM urunler
            WHERE urun_kodu = 'LP001'
            LIMIT 1
        """).fetchone()

        company_name = (
            "REDBOX GIDA"
            if redbox_product is not None
            else "REDBOX OS"
        )

        return {
            "ticari_unvan": company_name,
            "firma_kisa_ad": company_name,
            "tesis_kodu": None,
            "tesis_adi": None,
            "kullanim_modu": "GERCEK",
            "kurulum_tamamlandi": False,
            "legacy_kimlik": True,
        }

    return {
        "ticari_unvan": None,
        "firma_kisa_ad": "REDBOX OS",
        "tesis_kodu": None,
        "tesis_adi": None,
        "kullanim_modu": "KURULUM",
        "kurulum_tamamlandi": False,
        "legacy_kimlik": False,
    }


def ilk_kurulum_bilgilerini_getir(conn):
    setup = conn.execute("""
        SELECT
            kd.kullanim_modu,
            kd.tamamlandi,
            kd.baslama_zamani,
            kd.tamamlanma_zamani,
            fp.ticari_unvan,
            fp.kisa_ad,
            tp.tesis_kodu,
            tp.tesis_adi,
            kh.kullanici_adi,
            p.ad_soyad
        FROM ilk_kurulum_durumu kd
        LEFT JOIN firma_profili fp
          ON fp.id = kd.firma_id
        LEFT JOIN tesis_profilleri tp
          ON tp.id = kd.tesis_id
        LEFT JOIN kullanici_hesaplari kh
          ON kh.id = kd.ilk_yonetici_hesap_id
        LEFT JOIN personeller p
          ON p.id = kh.personel_id
        WHERE kd.id = 1
    """).fetchone()

    if setup is None:
        return None

    fields = (
        "kullanim_modu",
        "tamamlandi",
        "baslama_zamani",
        "tamamlanma_zamani",
        "ticari_unvan",
        "kisa_ad",
        "tesis_kodu",
        "tesis_adi",
        "kullanici_adi",
        "ad_soyad",
    )

    return dict(zip(fields, setup))


def ilk_kurulumu_tamamla(
    conn,
    firma,
    tesis,
    yonetici,
    kullanim_modu="GERCEK",
    oturum_id=None,
):
    if conn.in_transaction:
        raise RuntimeError(
            "İlk kurulum temiz bir bağlantıda "
            "başlatılmalıdır."
        )

    firma = firma or {}
    tesis = tesis or {}
    yonetici = yonetici or {}

    kullanim_modu = _text(
        kullanim_modu
    ).upper()

    if kullanim_modu not in KULLANIM_MODLARI:
        raise ValueError(
            "Kullanım modu GERCEK veya DEMO olmalıdır."
        )

    ticari_unvan = _required(
        firma,
        "ticari_unvan",
        "Ticari unvan",
    )
    kisa_ad = _required(
        firma,
        "kisa_ad",
        "Firma kısa adı",
    )
    tesis_kodu = _required(
        tesis,
        "tesis_kodu",
        "Tesis kodu",
    ).upper()
    tesis_adi = _required(
        tesis,
        "tesis_adi",
        "Tesis adı",
    )
    tesis_turu = _text(
        tesis.get("tesis_turu") or "URETIM"
    ).upper()
    ad_soyad = _required(
        yonetici,
        "ad_soyad",
        "Yönetici adı soyadı",
    )
    kullanici_adi = _required(
        yonetici,
        "kullanici_adi",
        "Kullanıcı adı",
    )
    parola = str(
        yonetici.get("parola") or ""
    )

    if len(ticari_unvan) < 2:
        raise ValueError(
            "Ticari unvan en az 2 karakter olmalıdır."
        )

    if len(kisa_ad) < 2:
        raise ValueError(
            "Firma kısa adı en az 2 karakter olmalıdır."
        )

    if not TESIS_KODU_PATTERN.fullmatch(tesis_kodu):
        raise ValueError(
            "Tesis kodu 2-50 karakter olmalı; yalnız "
            "harf, rakam, nokta, tire ve alt çizgi "
            "içermelidir."
        )

    if tesis_turu not in TESIS_TURLERI:
        raise ValueError("Geçersiz tesis türü.")

    if len(ad_soyad) < 3:
        raise ValueError(
            "Yönetici adı soyadı en az 3 karakter "
            "olmalıdır."
        )

    if not KULLANICI_ADI_PATTERN.fullmatch(
        kullanici_adi
    ):
        raise ValueError(
            "Kullanıcı adı 3-50 karakter olmalı; yalnız "
            "harf, rakam, nokta, tire ve alt çizgi "
            "içermelidir."
        )

    if len(parola) < 8:
        raise ValueError(
            "Parola en az 8 karakter olmalıdır."
        )

    now = datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )
    tuz = os.urandom(16).hex()
    parola_ozeti = parola_hash_olustur(
        parola,
        tuz,
    )

    conn.execute("BEGIN IMMEDIATE")

    try:
        setup_count = conn.execute("""
            SELECT COUNT(*)
            FROM ilk_kurulum_durumu
        """).fetchone()[0]

        company_count = conn.execute("""
            SELECT COUNT(*)
            FROM firma_profili
        """).fetchone()[0]

        facility_count = conn.execute("""
            SELECT COUNT(*)
            FROM tesis_profilleri
        """).fetchone()[0]

        account_count = conn.execute("""
            SELECT COUNT(*)
            FROM kullanici_hesaplari
        """).fetchone()[0]

        if (
            setup_count
            or company_count
            or facility_count
            or account_count
        ):
            raise RuntimeError(
                "İlk kurulum daha önce başlatılmış veya "
                "tamamlanmış."
            )

        conn.execute("""
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
                kayit_zamani
            )
            VALUES (
                1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?
            )
        """, (
            ticari_unvan,
            kisa_ad,
            _text(firma.get("vergi_dairesi")) or None,
            _text(firma.get("vergi_no")) or None,
            _text(firma.get("ulke")) or "Türkiye",
            _text(firma.get("il")) or None,
            _text(firma.get("ilce")) or None,
            _text(firma.get("adres")) or None,
            _text(firma.get("telefon")) or None,
            _text(firma.get("eposta")) or None,
            now,
        ))

        facility_cursor = conn.execute("""
            INSERT INTO tesis_profilleri (
                firma_id,
                tesis_kodu,
                tesis_adi,
                tesis_turu,
                ulke,
                il,
                ilce,
                adres,
                telefon,
                eposta,
                ana_tesis,
                aktif,
                kayit_zamani
            )
            VALUES (
                1, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?
            )
        """, (
            tesis_kodu,
            tesis_adi,
            tesis_turu,
            _text(tesis.get("ulke")) or "Türkiye",
            _text(tesis.get("il")) or None,
            _text(tesis.get("ilce")) or None,
            _text(tesis.get("adres")) or None,
            _text(tesis.get("telefon")) or None,
            _text(tesis.get("eposta")) or None,
            now,
        ))
        tesis_id = facility_cursor.lastrowid

        personnel = conn.execute("""
            SELECT id
            FROM personeller
            WHERE ad_soyad = ? COLLATE NOCASE
            LIMIT 1
        """, (ad_soyad,)).fetchone()

        if personnel is None:
            personnel_cursor = conn.execute("""
                INSERT INTO personeller (
                    ad_soyad,
                    gorev,
                    aktif,
                    aciklama,
                    kayit_zamani
                )
                VALUES (?, ?, 1, ?, ?)
            """, (
                ad_soyad,
                _text(
                    yonetici.get("gorev")
                    or "Sistem Yöneticisi"
                ),
                "İlk kurulum yönetici personeli",
                now,
            ))
            personel_id = personnel_cursor.lastrowid
        else:
            personel_id = int(personnel[0])
            conn.execute("""
                UPDATE personeller
                SET aktif = 1
                WHERE id = ?
            """, (personel_id,))

        account_cursor = conn.execute("""
            INSERT INTO kullanici_hesaplari (
                personel_id,
                kullanici_adi,
                parola_hash,
                parola_tuzu,
                iterasyon,
                yonetici,
                aktif,
                kayit_zamani
            )
            VALUES (?, ?, ?, ?, ?, 1, 1, ?)
        """, (
            personel_id,
            kullanici_adi,
            parola_ozeti,
            tuz,
            PBKDF2_ITERATIONS,
            now,
        ))
        hesap_id = account_cursor.lastrowid

        for yetki_kodu in ILK_YONETICI_YETKILERI:
            conn.execute("""
                INSERT INTO personel_yetkileri (
                    personel_id,
                    yetki_kodu,
                    aktif,
                    kayit_zamani
                )
                VALUES (?, ?, 1, ?)
                ON CONFLICT (
                    personel_id,
                    yetki_kodu
                )
                DO UPDATE SET aktif = 1
            """, (
                personel_id,
                yetki_kodu,
                now,
            ))

        conn.execute("""
            INSERT INTO ilk_kurulum_durumu (
                id,
                kullanim_modu,
                tamamlandi,
                firma_id,
                tesis_id,
                ilk_yonetici_hesap_id,
                baslama_zamani,
                tamamlanma_zamani,
                kurulum_surumu
            )
            VALUES (
                1, ?, 1, 1, ?, ?, ?, ?, 1
            )
        """, (
            kullanim_modu,
            tesis_id,
            hesap_id,
            now,
            now,
        ))

        audit_user = {
            "hesap_id": hesap_id,
            "personel_id": personel_id,
            "kullanici_adi": kullanici_adi,
            "ad_soyad": ad_soyad,
        }

        result = {
            "firma_id": 1,
            "tesis_id": tesis_id,
            "personel_id": personel_id,
            "hesap_id": hesap_id,
            "ticari_unvan": ticari_unvan,
            "tesis_kodu": tesis_kodu,
            "kullanici_adi": kullanici_adi,
            "kullanim_modu": kullanim_modu,
            "yetki_sayisi": len(
                ILK_YONETICI_YETKILERI
            ),
        }

        denetim_kaydi_ekle(
            conn,
            modul="SISTEM",
            islem="OLUSTURMA",
            kullanici=audit_user,
            kayit_turu="ilk_kurulum",
            kayit_id=1,
            aciklama=(
                "Firma, ana tesis ve ilk yönetici "
                "kurulumu atomik olarak tamamlandı."
            ),
            yeni_deger=result,
            oturum_id=oturum_id,
        )

        conn.commit()
        return result

    except Exception:
        conn.rollback()
        raise

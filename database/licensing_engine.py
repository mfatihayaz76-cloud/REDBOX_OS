import base64
import hashlib
import hmac
import json
import os
import platform
import re
import subprocess
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)

from database.audit_engine import denetim_kaydi_ekle


LICENSE_PREFIX = "RBX1"
PRODUCT_CODE = "REDBOX_OS"
LICENSE_CONTRACT_VERSION = 1

REQUIRED_PAYLOAD_FIELDS = {
    "sozlesme_surumu",
    "lisans_uuid",
    "urun_kodu",
    "acik_anahtar_kimligi",
    "firma_parmak_izi_sha256",
    "cihaz_parmak_izi_sha256",
    "lisans_turu",
    "baslangic_tarihi",
    "bitis_tarihi",
    "grace_period_gun",
    "duzenlenme_zamani",
}


def _normalize_text(value):
    return " ".join(str(value or "").strip().upper().split())


def _sha256_text(value):
    return hashlib.sha256(
        str(value).encode("utf-8")
    ).hexdigest()


def _is_sha256(value):
    if not isinstance(value, str) or len(value) != 64:
        return False

    try:
        int(value, 16)
    except ValueError:
        return False

    return value == value.lower()


def _urlsafe_b64decode(value):
    if not isinstance(value, str) or not value:
        raise ValueError("Base64URL değeri boş olamaz.")

    padding = "=" * (-len(value) % 4)

    try:
        return base64.urlsafe_b64decode(
            (value + padding).encode("ascii")
        )
    except Exception as exc:
        raise ValueError(
            "Geçersiz Base64URL değeri."
        ) from exc


def _public_key_from_base64(value):
    try:
        raw_key = base64.b64decode(
            str(value).encode("ascii"),
            validate=True,
        )
        return Ed25519PublicKey.from_public_bytes(raw_key)
    except Exception as exc:
        raise ValueError(
            "Geçersiz Ed25519 açık anahtarı."
        ) from exc


def _date_value(value, field_name):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} ISO YYYY-AA-GG biçiminde olmalıdır."
        ) from exc


def _now_date(simdi):
    if simdi is None:
        return datetime.now().astimezone().date()

    if isinstance(simdi, datetime):
        return simdi.date()

    if isinstance(simdi, date):
        return simdi

    return _date_value(simdi, "simdi")


def firma_parmak_izi_olustur(
    ticari_unvan,
    kisa_ad,
    vergi_no=None,
):
    ticari_unvan = _normalize_text(ticari_unvan)
    kisa_ad = _normalize_text(kisa_ad)
    vergi_no = _normalize_text(vergi_no)

    if not ticari_unvan:
        raise ValueError("Ticari unvan boş olamaz.")

    if not kisa_ad:
        raise ValueError("Firma kısa adı boş olamaz.")

    canonical = "|".join(
        (
            "REDBOX_OS_FIRMA_V1",
            ticari_unvan,
            kisa_ad,
            vergi_no,
        )
    )

    return _sha256_text(canonical)


def _macos_platform_uuid():
    result = subprocess.run(
        [
            "ioreg",
            "-rd1",
            "-c",
            "IOPlatformExpertDevice",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    if result.returncode != 0:
        return None

    match = re.search(
        r'"IOPlatformUUID"\s*=\s*"([^"]+)"',
        result.stdout,
    )

    return match.group(1) if match else None


def _windows_machine_guid():
    try:
        import winreg
    except ImportError:
        return None

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        ) as key:
            value, _ = winreg.QueryValueEx(
                key,
                "MachineGuid",
            )
            return value
    except OSError:
        return None


def _linux_machine_id():
    for name in (
        "/etc/machine-id",
        "/var/lib/dbus/machine-id",
    ):
        path = Path(name)

        try:
            value = path.read_text(
                encoding="utf-8"
            ).strip()
        except OSError:
            continue

        if value:
            return value

    return None


def _device_source_value():
    if sys.platform == "darwin":
        value = _macos_platform_uuid()
        if value:
            return "MACOS_PLATFORM_UUID", value

    if os.name == "nt":
        value = _windows_machine_guid()
        if value:
            return "WINDOWS_MACHINE_GUID", value

    value = _linux_machine_id()
    if value:
        return "LINUX_MACHINE_ID", value

    fallback = "|".join(
        (
            str(uuid.getnode()),
            platform.system(),
            platform.machine(),
            platform.node(),
        )
    )
    return "PORTABLE_FALLBACK", fallback


def cihaz_parmak_izi_olustur(
    ham_cihaz_kimligi=None,
    kaynak=None,
):
    if ham_cihaz_kimligi is None:
        source_name, raw_value = _device_source_value()
    else:
        source_name = _normalize_text(
            kaynak or "CONTROLLED_INPUT"
        )
        raw_value = str(ham_cihaz_kimligi).strip()

    if not raw_value:
        raise ValueError("Cihaz kimliği boş olamaz.")

    canonical = "|".join(
        (
            "REDBOX_OS_CIHAZ_V1",
            source_name,
            raw_value,
        )
    )

    return {
        "cihaz_parmak_izi_sha256": _sha256_text(
            canonical
        ),
        "kaynak": source_name,
    }


def lisans_anahtari_sha256(lisans_anahtari):
    value = str(lisans_anahtari or "").strip()

    if not value:
        raise ValueError("Lisans anahtarı boş olamaz.")

    return _sha256_text(value)


def lisans_anahtarini_dogrula(
    lisans_anahtari,
    acik_anahtarlar,
    firma_parmak_izi_sha256,
    cihaz_parmak_izi_sha256,
    simdi=None,
):
    token = str(lisans_anahtari or "").strip()

    if not token:
        raise ValueError("Lisans anahtarı boş olamaz.")

    if not _is_sha256(firma_parmak_izi_sha256):
        raise ValueError("Firma parmak izi geçersiz.")

    if not _is_sha256(cihaz_parmak_izi_sha256):
        raise ValueError("Cihaz parmak izi geçersiz.")

    parts = token.split(".")

    if len(parts) != 3 or parts[0] != LICENSE_PREFIX:
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "ANAHTAR_BICIMI_GECERSIZ",
        }

    try:
        payload_bytes = _urlsafe_b64decode(parts[1])
        signature = _urlsafe_b64decode(parts[2])
        payload = json.loads(
            payload_bytes.decode("utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "ANAHTAR_COZULEMEDI",
        }

    if not isinstance(payload, dict):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "PAYLOAD_NESNE_DEGIL",
        }

    if set(payload) != REQUIRED_PAYLOAD_FIELDS:
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "PAYLOAD_ALANLARI_GECERSIZ",
        }

    canonical_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    if not hmac.compare_digest(
        payload_bytes,
        canonical_bytes,
    ):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "PAYLOAD_KANONIK_DEGIL",
        }

    key_id = payload["acik_anahtar_kimligi"]
    public_key_value = (
        acik_anahtarlar.get(key_id)
        if isinstance(acik_anahtarlar, dict)
        else None
    )

    if not public_key_value:
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "ACIK_ANAHTAR_BULUNAMADI",
        }

    try:
        public_key = _public_key_from_base64(
            public_key_value
        )
        public_key.verify(signature, payload_bytes)
    except (InvalidSignature, ValueError):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "IMZA_GECERSIZ",
        }

    if payload["sozlesme_surumu"] != LICENSE_CONTRACT_VERSION:
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "SOZLESME_SURUMU_DESTEKLENMIYOR",
        }

    if payload["urun_kodu"] != PRODUCT_CODE:
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "URUN_KODU_UYUSMUYOR",
        }

    license_type = payload["lisans_turu"]

    if license_type not in {"SURELI", "SURESIZ"}:
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "LISANS_TURU_GECERSIZ",
        }

    grace_days = payload["grace_period_gun"]

    if (
        not isinstance(grace_days, int)
        or isinstance(grace_days, bool)
        or not 0 <= grace_days <= 30
    ):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "GRACE_PERIOD_GECERSIZ",
        }

    try:
        start_date = _date_value(
            payload["baslangic_tarihi"],
            "baslangic_tarihi",
        )
        end_value = payload["bitis_tarihi"]
        end_date = (
            _date_value(end_value, "bitis_tarihi")
            if end_value is not None
            else None
        )
        datetime.fromisoformat(
            payload["duzenlenme_zamani"]
        )
    except (TypeError, ValueError):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "TARIH_BICIMI_GECERSIZ",
        }

    if (
        license_type == "SURELI"
        and end_date is None
    ):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "BITIS_TARIHI_ZORUNLU",
        }

    if (
        license_type == "SURESIZ"
        and end_date is not None
    ):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "SURESIZ_BITIS_TARIHI_OLAMAZ",
        }

    if (
        end_date is not None
        and end_date < start_date
    ):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "TARIH_ARALIGI_GECERSIZ",
        }

    if not hmac.compare_digest(
        payload["firma_parmak_izi_sha256"],
        firma_parmak_izi_sha256,
    ):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "FIRMA_UYUSMUYOR",
        }

    if not hmac.compare_digest(
        payload["cihaz_parmak_izi_sha256"],
        cihaz_parmak_izi_sha256,
    ):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "CIHAZ_UYUSMUYOR",
        }

    today = _now_date(simdi)

    if today < start_date:
        return {
            "gecerli": False,
            "durum": "BASLAMADI",
            "neden_kodu": "LISANS_HENUZ_BASLAMADI",
            "payload": payload,
        }

    if license_type == "SURELI" and today > end_date:
        grace_end = end_date + timedelta(
            days=grace_days
        )

        if today <= grace_end:
            return {
                "gecerli": True,
                "durum": "GRACE",
                "neden_kodu": "GRACE_PERIOD_AKTIF",
                "kalan_grace_gun": (
                    grace_end - today
                ).days,
                "payload": payload,
            }

        return {
            "gecerli": False,
            "durum": "SURESI_DOLDU",
            "neden_kodu": "LISANS_SURESI_DOLDU",
            "payload": payload,
        }

    return {
        "gecerli": True,
        "durum": "AKTIF",
        "neden_kodu": "LISANS_GECERLI",
        "payload": payload,
    }


def _activation_datetime(simdi):
    if simdi is None:
        return datetime.now().astimezone()

    if isinstance(simdi, datetime):
        if simdi.tzinfo is None:
            return simdi.astimezone()
        return simdi

    if isinstance(simdi, date):
        return datetime(
            simdi.year,
            simdi.month,
            simdi.day,
        ).astimezone()

    try:
        parsed = datetime.fromisoformat(str(simdi))
    except ValueError as exc:
        raise ValueError(
            "Aktivasyon zamanı ISO biçiminde olmalıdır."
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.astimezone()

    return parsed


def _company_fingerprint_from_db(conn, firma_id):
    row = conn.execute(
        """
        SELECT
            ticari_unvan,
            kisa_ad,
            vergi_no,
            aktif
        FROM firma_profili
        WHERE id = ?
        """,
        (firma_id,),
    ).fetchone()

    if row is None:
        raise ValueError("Firma profili bulunamadı.")

    if int(row[3]) != 1:
        raise ValueError("Firma profili aktif değil.")

    return firma_parmak_izi_olustur(
        row[0],
        row[1],
        row[2],
    )


def lisansi_aktive_et(
    conn,
    lisans_anahtari,
    acik_anahtarlar,
    firma_id,
    cihaz_parmak_izi_sha256,
    kullanici=None,
    oturum_id=None,
    simdi=None,
):
    if conn.in_transaction:
        raise RuntimeError(
            "Lisans aktivasyonu temiz transaction gerektirir."
        )

    company_hash = _company_fingerprint_from_db(
        conn,
        firma_id,
    )
    activation_time = _activation_datetime(simdi)
    validation = lisans_anahtarini_dogrula(
        lisans_anahtari,
        acik_anahtarlar,
        company_hash,
        cihaz_parmak_izi_sha256,
        simdi=activation_time,
    )

    if not validation.get("gecerli"):
        raise ValueError(
            "Lisans doğrulanamadı: "
            + validation.get(
                "neden_kodu",
                "BILINMEYEN_HATA",
            )
        )

    payload = validation["payload"]
    token_hash = lisans_anahtari_sha256(
        lisans_anahtari
    )
    token_parts = str(lisans_anahtari).strip().split(".")
    payload_json = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    timestamp = activation_time.isoformat()
    status = validation["durum"]

    try:
        conn.execute("BEGIN IMMEDIATE")

        existing = conn.execute(
            """
            SELECT id
            FROM lisans_kayitlari
            WHERE firma_id = ?
              AND durum IN ('AKTIF', 'GRACE')
            LIMIT 1
            """,
            (firma_id,),
        ).fetchone()

        if existing is not None:
            raise RuntimeError(
                "Firma için aktif lisans zaten mevcut."
            )

        cursor = conn.execute(
            """
            INSERT INTO lisans_kayitlari (
                lisans_uuid,
                lisans_anahtari_sha256,
                firma_id,
                cihaz_parmak_izi_sha256,
                urun_kodu,
                lisans_turu,
                durum,
                baslangic_tarihi,
                bitis_tarihi,
                grace_period_gun,
                lisans_surumu,
                imzali_payload_json,
                imza_base64,
                acik_anahtar_kimligi,
                aktivasyon_zamani,
                son_dogrulama_zamani,
                son_basarili_dogrulama_zamani,
                son_guvenilir_zaman,
                kayit_zamani,
                guncelleme_zamani
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                payload["lisans_uuid"],
                token_hash,
                firma_id,
                cihaz_parmak_izi_sha256,
                payload["urun_kodu"],
                payload["lisans_turu"],
                status,
                payload["baslangic_tarihi"],
                payload["bitis_tarihi"],
                payload["grace_period_gun"],
                payload["sozlesme_surumu"],
                payload_json,
                token_parts[2],
                payload["acik_anahtar_kimligi"],
                timestamp,
                timestamp,
                timestamp,
                timestamp,
                timestamp,
                timestamp,
            ),
        )
        license_id = cursor.lastrowid

        validation_cursor = conn.execute(
            """
            INSERT INTO lisans_dogrulama_kayitlari (
                lisans_id,
                kontrol_zamani,
                sonuc,
                kaynak,
                neden_kodu,
                aciklama,
                cihaz_parmak_izi_sha256,
                cevrimdisi,
                oturum_id
            )
            VALUES (?, ?, ?, 'AKTIVASYON', ?, ?, ?, 1, ?)
            """,
            (
                license_id,
                timestamp,
                (
                    "GRACE"
                    if status == "GRACE"
                    else "BASARILI"
                ),
                validation["neden_kodu"],
                "Ed25519 imzalı çevrimdışı lisans doğrulandı.",
                cihaz_parmak_izi_sha256,
                oturum_id,
            ),
        )

        conn.execute(
            """
            UPDATE lisans_gecis_durumu
            SET
                durum = 'TAMAMLANDI',
                tamamlanma_zamani = ?
            WHERE id = 1
              AND durum = 'AKTIF'
            """,
            (timestamp,),
        )

        denetim_kaydi_ekle(
            conn,
            modul="LISANS",
            islem="OLUSTURMA",
            kullanici=kullanici,
            kayit_turu="lisans_aktivasyonu",
            kayit_id=license_id,
            aciklama=(
                "Firma ve cihaz bağlı lisans aktive edildi."
            ),
            yeni_deger={
                "lisans_uuid": payload["lisans_uuid"],
                "lisans_turu": payload["lisans_turu"],
                "durum": status,
                "bitis_tarihi": payload["bitis_tarihi"],
                "cihaz_parmak_izi_sha256": (
                    cihaz_parmak_izi_sha256
                ),
            },
            oturum_id=oturum_id,
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return {
        "lisans_id": license_id,
        "dogrulama_kaydi_id": (
            validation_cursor.lastrowid
        ),
        "lisans_uuid": payload["lisans_uuid"],
        "lisans_turu": payload["lisans_turu"],
        "durum": status,
        "bitis_tarihi": payload["bitis_tarihi"],
        "grace_period_gun": payload["grace_period_gun"],
        "lisans_anahtari_sha256": token_hash,
    }


def _urlsafe_b64encode(value):
    return base64.urlsafe_b64encode(
        value
    ).decode("ascii").rstrip("=")


def aktif_lisans_durumunu_getir(
    conn,
    acik_anahtarlar,
    cihaz_parmak_izi_sha256,
    simdi=None,
):
    if not _is_sha256(cihaz_parmak_izi_sha256):
        raise ValueError("Cihaz parmak izi geçersiz.")

    row = conn.execute(
        """
        SELECT
            id,
            lisans_uuid,
            lisans_anahtari_sha256,
            firma_id,
            cihaz_parmak_izi_sha256,
            durum,
            imzali_payload_json,
            imza_base64,
            son_guvenilir_zaman
        FROM lisans_kayitlari
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    if row is None:
        return {
            "gecerli": False,
            "durum": "LISANS_YOK",
            "neden_kodu": "AKTIF_LISANS_BULUNAMADI",
        }

    stored_status = row[5]

    if stored_status in {
        "ASKIDA",
        "IPTAL",
        "SURESI_DOLDU",
    }:
        return {
            "gecerli": False,
            "durum": stored_status,
            "neden_kodu": (
                "LISANS_" + stored_status
            ),
            "lisans_id": row[0],
            "lisans_uuid": row[1],
        }

    if not hmac.compare_digest(
        row[4],
        cihaz_parmak_izi_sha256,
    ):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "CIHAZ_UYUSMUYOR",
            "lisans_id": row[0],
            "lisans_uuid": row[1],
        }

    current_time = _activation_datetime(simdi)
    trusted_value = row[8]

    if trusted_value:
        try:
            trusted_time = datetime.fromisoformat(
                trusted_value
            )
        except ValueError:
            return {
                "gecerli": False,
                "durum": "GECERSIZ",
                "neden_kodu": "GUVENILIR_ZAMAN_BOZUK",
                "lisans_id": row[0],
                "lisans_uuid": row[1],
            }

        if trusted_time.tzinfo is None:
            trusted_time = trusted_time.astimezone()

        if (
            current_time
            < trusted_time - timedelta(minutes=5)
        ):
            return {
                "gecerli": False,
                "durum": "GECERSIZ",
                "neden_kodu": "SISTEM_SAATI_GERI_ALINDI",
                "lisans_id": row[0],
                "lisans_uuid": row[1],
            }

    try:
        payload = json.loads(row[6])
        canonical_payload = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, json.JSONDecodeError):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "KAYITLI_PAYLOAD_BOZUK",
            "lisans_id": row[0],
            "lisans_uuid": row[1],
        }

    token = (
        LICENSE_PREFIX
        + "."
        + _urlsafe_b64encode(canonical_payload)
        + "."
        + row[7]
    )

    if not hmac.compare_digest(
        lisans_anahtari_sha256(token),
        row[2],
    ):
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "LISANS_KAYDI_DEGISTIRILMIS",
            "lisans_id": row[0],
            "lisans_uuid": row[1],
        }

    try:
        company_hash = _company_fingerprint_from_db(
            conn,
            row[3],
        )
    except ValueError:
        return {
            "gecerli": False,
            "durum": "GECERSIZ",
            "neden_kodu": "FIRMA_PROFILI_GECERSIZ",
            "lisans_id": row[0],
            "lisans_uuid": row[1],
        }

    result = lisans_anahtarini_dogrula(
        token,
        acik_anahtarlar,
        company_hash,
        cihaz_parmak_izi_sha256,
        simdi=current_time,
    )
    result["lisans_id"] = row[0]
    result["lisans_uuid"] = row[1]
    result["kayitli_durum"] = stored_status

    return result


def lisans_erisim_karari(
    conn,
    acik_anahtarlar,
    cihaz_parmak_izi_sha256,
    simdi=None,
):
    current_time = _activation_datetime(simdi)

    license_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM lisans_kayitlari
        """
    ).fetchone()[0]

    if license_count > 0:
        license_status = aktif_lisans_durumunu_getir(
            conn,
            acik_anahtarlar,
            cihaz_parmak_izi_sha256,
            simdi=current_time,
        )
        return {
            **license_status,
            "erisim_izni": bool(
                license_status.get("gecerli")
            ),
            "akis": "LISANS",
        }

    active_accounts = conn.execute(
        """
        SELECT COUNT(*)
        FROM kullanici_hesaplari
        WHERE aktif = 1
        """
    ).fetchone()[0]

    completed_setup = conn.execute(
        """
        SELECT tamamlandi
        FROM ilk_kurulum_durumu
        WHERE id = 1
        """
    ).fetchone()

    setup_complete = bool(
        completed_setup
        and int(completed_setup[0]) == 1
    )

    if active_accounts == 0 and not setup_complete:
        return {
            "erisim_izni": True,
            "gecerli": False,
            "durum": "ILK_KURULUM",
            "neden_kodu": "ILK_KURULUM_TAMAMLANMALI",
            "akis": "ILK_KURULUM",
        }

    transition = conn.execute(
        """
        SELECT
            durum,
            baslangic_zamani,
            bitis_zamani,
            gecis_suresi_gun
        FROM lisans_gecis_durumu
        WHERE id = 1
        """
    ).fetchone()

    if transition is not None:
        try:
            transition_end = datetime.fromisoformat(
                transition[2]
            )
        except ValueError:
            return {
                "erisim_izni": False,
                "gecerli": False,
                "durum": "GECERSIZ",
                "neden_kodu": "GECIS_KAYDI_BOZUK",
                "akis": "LISANS_AKTIVASYONU",
            }

        if transition_end.tzinfo is None:
            transition_end = transition_end.astimezone()

        if (
            transition[0] == "AKTIF"
            and current_time <= transition_end
        ):
            remaining_days = max(
                0,
                (
                    transition_end.date()
                    - current_time.date()
                ).days,
            )
            return {
                "erisim_izni": True,
                "gecerli": False,
                "durum": "GECIS_SURESI",
                "neden_kodu": "LEGACY_GECIS_SURESI_AKTIF",
                "kalan_gun": remaining_days,
                "bitis_zamani": transition[2],
                "akis": "NORMAL_GIRIS",
            }

        return {
            "erisim_izni": False,
            "gecerli": False,
            "durum": "GECIS_SURESI_DOLDU",
            "neden_kodu": "LEGACY_GECIS_SURESI_DOLDU",
            "bitis_zamani": transition[2],
            "akis": "LISANS_AKTIVASYONU",
        }

    return {
        "erisim_izni": False,
        "gecerli": False,
        "durum": "LISANS_GEREKLI",
        "neden_kodu": "AKTIF_LISANS_BULUNAMADI",
        "akis": "LISANS_AKTIVASYONU",
    }


def _license_resource_path(*parts):
    project_root = Path(__file__).resolve().parent.parent
    bundle_root = Path(
        getattr(
            sys,
            "_MEIPASS",
            project_root,
        )
    )
    return bundle_root.joinpath(*parts)


def lisans_acik_anahtarlarini_yukle(
    registry_path=None,
):
    path = (
        Path(registry_path)
        if registry_path is not None
        else _license_resource_path(
            "licensing",
            "public_keys.json",
        )
    )

    if not path.is_file():
        raise FileNotFoundError(
            "Lisans açık anahtar kayıt dosyası bulunamadı: "
            + str(path)
        )

    try:
        registry = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Lisans açık anahtar kayıt dosyası bozuk."
        ) from exc

    if not isinstance(registry, dict):
        raise ValueError(
            "Açık anahtar kayıt kökü nesne olmalıdır."
        )

    if registry.get("registry_version") != 1:
        raise ValueError(
            "Açık anahtar kayıt sürümü desteklenmiyor."
        )

    if registry.get("product_code") != PRODUCT_CODE:
        raise ValueError(
            "Açık anahtar kayıt ürün kodu geçersiz."
        )

    keys = registry.get("keys")

    if not isinstance(keys, list) or not keys:
        raise ValueError(
            "Açık anahtar kayıt listesi boş olamaz."
        )

    active_keys = {}

    for record in keys:
        if not isinstance(record, dict):
            raise ValueError(
                "Açık anahtar kaydı nesne olmalıdır."
            )

        key_id = str(
            record.get("key_id") or ""
        ).strip()
        algorithm = record.get("algorithm")
        public_value = record.get(
            "public_key_base64"
        )
        expected_sha = record.get(
            "public_key_sha256"
        )
        active = record.get("active")

        if not key_id:
            raise ValueError(
                "Açık anahtar kimliği boş olamaz."
            )

        if key_id in active_keys:
            raise ValueError(
                "Yinelenen açık anahtar kimliği: "
                + key_id
            )

        if algorithm != "Ed25519":
            raise ValueError(
                "Desteklenmeyen lisans imza algoritması."
            )

        try:
            raw_key = base64.b64decode(
                str(public_value).encode("ascii"),
                validate=True,
            )
            Ed25519PublicKey.from_public_bytes(
                raw_key
            )
        except Exception as exc:
            raise ValueError(
                "Geçersiz Ed25519 açık anahtar kaydı."
            ) from exc

        if len(raw_key) != 32:
            raise ValueError(
                "Ed25519 açık anahtarı 32 byte olmalıdır."
            )

        actual_sha = hashlib.sha256(
            raw_key
        ).hexdigest()

        if not hmac.compare_digest(
            actual_sha,
            str(expected_sha),
        ):
            raise ValueError(
                "Açık anahtar SHA-256 doğrulaması başarısız."
            )

        if active is True:
            active_keys[key_id] = public_value
        elif active is not False:
            raise ValueError(
                "Açık anahtar aktiflik değeri boolean olmalıdır."
            )

    if not active_keys:
        raise ValueError(
            "Aktif lisans açık anahtarı bulunamadı."
        )

    return active_keys


def lisans_talep_bilgilerini_getir(
    conn,
    cihaz_bilgisi=None,
    simdi=None,
):
    profile = conn.execute(
        """
        SELECT
            id,
            ticari_unvan,
            kisa_ad,
            vergi_no,
            ulke,
            il,
            ilce,
            aktif
        FROM firma_profili
        WHERE id = 1
        """
    ).fetchone()

    if profile is None:
        return {
            "hazir": False,
            "neden_kodu": "FIRMA_PROFILI_GEREKLI",
        }

    if int(profile[7]) != 1:
        return {
            "hazir": False,
            "neden_kodu": "FIRMA_PROFILI_AKTIF_DEGIL",
        }

    device = (
        cihaz_bilgisi
        if cihaz_bilgisi is not None
        else cihaz_parmak_izi_olustur()
    )
    device_hash = device.get(
        "cihaz_parmak_izi_sha256"
    )

    if not _is_sha256(device_hash):
        raise ValueError(
            "Talep cihaz parmak izi geçersiz."
        )

    company_hash = firma_parmak_izi_olustur(
        profile[1],
        profile[2],
        profile[3],
    )
    request_time = _activation_datetime(simdi)

    return {
        "hazir": True,
        "talep_surumu": 1,
        "talep_uuid": uuid.uuid4().hex,
        "urun_kodu": PRODUCT_CODE,
        "firma_id": profile[0],
        "ticari_unvan": profile[1],
        "firma_kisa_ad": profile[2],
        "vergi_no": profile[3],
        "ulke": profile[4],
        "il": profile[5],
        "ilce": profile[6],
        "firma_parmak_izi_sha256": company_hash,
        "cihaz_parmak_izi_sha256": device_hash,
        "cihaz_kaynagi": device.get("kaynak"),
        "talep_zamani": request_time.isoformat(),
    }

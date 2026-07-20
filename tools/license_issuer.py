import argparse
import base64
import getpass
import json
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from database.licensing_engine import (
    LICENSE_CONTRACT_VERSION,
    LICENSE_PREFIX,
    PRODUCT_CODE,
)


def _is_sha256(value):
    if not isinstance(value, str) or len(value) != 64:
        return False

    try:
        int(value, 16)
    except ValueError:
        return False

    return value == value.lower()


def _b64url(value):
    return base64.urlsafe_b64encode(
        value
    ).decode("ascii").rstrip("=")


def lisans_anahtari_uret(
    talep,
    private_key,
    key_id,
    lisans_turu,
    baslangic_tarihi,
    bitis_tarihi=None,
    grace_period_gun=7,
    duzenlenme_zamani=None,
    lisans_uuid=None,
):
    if not isinstance(talep, dict):
        raise ValueError("Lisans talebi nesne olmalıdır.")

    if talep.get("talep_surumu") != 1:
        raise ValueError("Talep sürümü desteklenmiyor.")

    if talep.get("urun_kodu") != PRODUCT_CODE:
        raise ValueError("Talep ürün kodu geçersiz.")

    company_hash = talep.get(
        "firma_parmak_izi_sha256"
    )
    device_hash = talep.get(
        "cihaz_parmak_izi_sha256"
    )

    if not _is_sha256(company_hash):
        raise ValueError("Firma parmak izi geçersiz.")

    if not _is_sha256(device_hash):
        raise ValueError("Cihaz parmak izi geçersiz.")

    license_type = str(lisans_turu).strip().upper()

    if license_type not in {"SURELI", "SURESIZ"}:
        raise ValueError("Lisans türü geçersiz.")

    try:
        start_date = date.fromisoformat(
            str(baslangic_tarihi)
        )
    except ValueError as exc:
        raise ValueError(
            "Başlangıç tarihi YYYY-AA-GG olmalıdır."
        ) from exc

    if license_type == "SURELI":
        if bitis_tarihi is None:
            raise ValueError(
                "Süreli lisans için bitiş tarihi zorunludur."
            )

        try:
            end_date = date.fromisoformat(
                str(bitis_tarihi)
            )
        except ValueError as exc:
            raise ValueError(
                "Bitiş tarihi YYYY-AA-GG olmalıdır."
            ) from exc

        if end_date < start_date:
            raise ValueError(
                "Bitiş tarihi başlangıçtan önce olamaz."
            )

        end_value = end_date.isoformat()
    else:
        if bitis_tarihi not in (None, ""):
            raise ValueError(
                "Süresiz lisansın bitiş tarihi olamaz."
            )

        end_value = None

    grace_days = int(grace_period_gun)

    if not 0 <= grace_days <= 30:
        raise ValueError(
            "Grace period 0-30 gün arasında olmalıdır."
        )

    issued_at = (
        duzenlenme_zamani.isoformat()
        if isinstance(duzenlenme_zamani, datetime)
        else str(duzenlenme_zamani)
        if duzenlenme_zamani is not None
        else datetime.now().astimezone().isoformat()
    )

    payload = {
        "sozlesme_surumu": LICENSE_CONTRACT_VERSION,
        "lisans_uuid": (
            str(lisans_uuid)
            if lisans_uuid is not None
            else "LIC-" + uuid.uuid4().hex.upper()
        ),
        "urun_kodu": PRODUCT_CODE,
        "acik_anahtar_kimligi": str(key_id),
        "firma_parmak_izi_sha256": company_hash,
        "cihaz_parmak_izi_sha256": device_hash,
        "lisans_turu": license_type,
        "baslangic_tarihi": start_date.isoformat(),
        "bitis_tarihi": end_value,
        "grace_period_gun": grace_days,
        "duzenlenme_zamani": issued_at,
    }

    payload_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    signature = private_key.sign(payload_bytes)

    return (
        LICENSE_PREFIX
        + "."
        + _b64url(payload_bytes)
        + "."
        + _b64url(signature)
    ), payload


def _load_request(path):
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Lisans talep dosyası bozuk."
        ) from exc

    if not isinstance(value, dict):
        raise ValueError(
            "Lisans talep dosyası nesne olmalıdır."
        )

    return value


def _find_private_key(authority, key_id):
    path = (
        Path(authority)
        / "private"
        / (
            key_id
            + "_ed25519_private_encrypted.pem"
        )
    )

    if not path.is_file():
        raise FileNotFoundError(
            "Şifreli özel anahtar bulunamadı: "
            + str(path)
        )

    return path


def main():
    parser = argparse.ArgumentParser(
        description=(
            "REDBOX OS çevrimdışı Ed25519 lisans üretim aracı"
        )
    )
    parser.add_argument("--request", required=True)
    parser.add_argument(
        "--type",
        required=True,
        choices=("SURELI", "SURESIZ"),
    )
    parser.add_argument("--start", required=True)
    parser.add_argument("--end")
    parser.add_argument(
        "--grace-days",
        type=int,
        default=7,
    )
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--authority",
        default=str(
            Path.home()
            / "REDBOX_OS_LICENSE_AUTHORITY"
        ),
    )
    parser.add_argument(
        "--key-id",
        default="REDBOX-PROD-2813E117AB41",
    )
    args = parser.parse_args()

    request = _load_request(args.request)
    private_path = _find_private_key(
        args.authority,
        args.key_id,
    )
    password = getpass.getpass(
        "Üretim özel anahtarı parolası: "
    )

    try:
        private_key = (
            serialization.load_pem_private_key(
                private_path.read_bytes(),
                password=password.encode("utf-8"),
            )
        )
    except Exception as exc:
        raise SystemExit(
            "HATA: Özel anahtar açılamadı."
        ) from exc

    token, payload = lisans_anahtari_uret(
        request,
        private_key,
        args.key_id,
        args.type,
        args.start,
        bitis_tarihi=args.end,
        grace_period_gun=args.grace_days,
    )

    output = Path(args.output).resolve()

    if output.exists():
        raise SystemExit(
            "HATA: Çıktı dosyası zaten mevcut."
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output.write_text(
        token + "\n",
        encoding="utf-8",
    )

    print("=" * 90)
    print("REDBOX OS LICENSE ISSUED")
    print("=" * 90)
    print("LICENSE UUID :", payload["lisans_uuid"])
    print("TYPE         :", payload["lisans_turu"])
    print("START        :", payload["baslangic_tarihi"])
    print("END          :", payload["bitis_tarihi"])
    print("GRACE DAYS   :", payload["grace_period_gun"])
    print("KEY ID       :", payload["acik_anahtar_kimligi"])
    print("OUTPUT       :", output)
    print("PRIVATE KEY  : NOT EXPORTED")
    print("LICENSE KEY  : NOT PRINTED")


if __name__ == "__main__":
    main()

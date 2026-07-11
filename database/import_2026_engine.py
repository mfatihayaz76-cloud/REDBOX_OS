from datetime import datetime

from database.import_2026_data import (
    URETIMLER_2026,
)

from database.import_2026_depo_data import (
    DEPO_KABULLER_2026,
)


PARTI_TEORIK_KG = 20.412
PARTI_PROSES_SUYU_KG = 10.700

RECETE = {
    "Patates Unu": 5.200,
    "Nişasta": 2.560,
    "Mısır Unu": 1.280,
    "Metilselüloz Benecel A4M E461": 0.120,
    "Tavuk Çeşnisi": 0.320,
    "Sarımsak Tozu": 0.064,
    "Karabiber": 0.024,
    "Tuz": 0.144,
}


def tarih_dogrula(
    deger,
    alan,
):
    if not deger:
        raise ValueError(
            f"{alan} boş bırakılamaz."
        )

    tarih = datetime.strptime(
        deger,
        "%d.%m.%Y",
    )

    if tarih.year != 2026:
        raise ValueError(
            f"{alan} 2026 yılına ait değil: "
            f"{deger}"
        )

    return tarih


def depo_verisi_dogrula():
    depo_map = {}

    for row in DEPO_KABULLER_2026:
        hammadde = row["hammadde"]

        if hammadde not in RECETE:
            raise ValueError(
                "Reçetede olmayan depo hammaddesi: "
                f"{hammadde}"
            )

        if hammadde in depo_map:
            raise ValueError(
                "Staging verisinde aynı hammadde "
                "birden fazla kez bulundu: "
                f"{hammadde}"
            )

        tarih_dogrula(
            row["kabul_tarihi"],
            f"{hammadde} kabul tarihi",
        )

        miktar = row["miktar_kg"]

        if miktar is None:
            raise ValueError(
                f"{hammadde} depo miktarı eksik."
            )

        if float(miktar) <= 0:
            raise ValueError(
                f"{hammadde} depo miktarı "
                "0'dan büyük olmalıdır."
            )

        if (
            hammadde
            == "Metilselüloz Benecel A4M E461"
            and str(
                row["tedarikci_lot_no"]
            ).strip()
            != "2743063"
        ):
            raise ValueError(
                "Benecel lotu 2743063 olmalıdır."
            )

        depo_map[hammadde] = float(
            miktar
        )

    eksik_hammaddeler = (
        set(RECETE)
        - set(depo_map)
    )

    if eksik_hammaddeler:
        raise ValueError(
            "Depo staging verisinde eksik "
            "hammaddeler: "
            + ", ".join(
                sorted(
                    eksik_hammaddeler
                )
            )
        )

    return depo_map


def uretim_verisi_dogrula():
    lotlar = set()
    toplam_parti = 0
    eksik_alanlar = []

    for row in URETIMLER_2026:
        tarih_dogrula(
            row["uretim_tarihi"],
            "Üretim tarihi",
        )

        lot_no = str(
            row["urun_lot_no"] or ""
        ).strip()

        if not lot_no:
            eksik_alanlar.append(
                (
                    row["uretim_tarihi"],
                    "ÜRÜN LOT NO",
                )
            )

        elif lot_no in lotlar:
            raise ValueError(
                "Tekrar eden ürün lotu: "
                f"{lot_no}"
            )

        else:
            lotlar.add(
                lot_no
            )

        parti = int(
            row["parti_sayisi"]
        )

        if parti <= 0:
            raise ValueError(
                "Parti sayısı 0'dan büyük "
                "olmalıdır."
            )

        toplam_parti += parti

        if (
            row["uretim_firesi_kg"]
            is None
        ):
            eksik_alanlar.append(
                (
                    row["uretim_tarihi"],
                    "ÜRETİM FİRESİ KG",
                )
            )

    return (
        toplam_parti,
        eksik_alanlar,
    )


def kutle_denklemi_dogrula(
    depo_map,
    toplam_parti,
):
    sonuclar = []

    for hammadde, parti_kg in RECETE.items():
        giris = round(
            depo_map[hammadde],
            3,
        )

        tuketim = round(
            parti_kg * toplam_parti,
            3,
        )

        kalan = round(
            giris - tuketim,
            3,
        )

        sonuclar.append({
            "hammadde": hammadde,
            "giris": giris,
            "tuketim": tuketim,
            "kalan": kalan,
        })

    hatali = [
        row
        for row in sonuclar
        if abs(
            row["kalan"]
        ) > 0.001
    ]

    if hatali:
        mesaj = []

        for row in hatali:
            mesaj.append(
                f'{row["hammadde"]}: '
                f'giriş {row["giris"]:.3f}, '
                f'tüketim '
                f'{row["tuketim"]:.3f}, '
                f'kalan {row["kalan"]:.3f}'
            )

        raise ValueError(
            "Hammadde kütle denkliği "
            "kapanmadı:\n"
            + "\n".join(
                mesaj
            )
        )

    return sonuclar


def aktarim_on_kontrol():
    print(
        "=== REDBOX OS 2026 AKTARIM "
        "FINAL PREFLIGHT ==="
    )

    depo_map = depo_verisi_dogrula()

    (
        toplam_parti,
        eksik_alanlar,
    ) = uretim_verisi_dogrula()

    kutle = kutle_denklemi_dogrula(
        depo_map,
        toplam_parti,
    )

    print("")
    print(
        "TOPLAM URETIM KAYDI:",
        len(URETIMLER_2026),
    )

    print(
        "TOPLAM PARTI:",
        toplam_parti,
    )

    print(
        "TEORIK URETIM:",
        f"{toplam_parti * PARTI_TEORIK_KG:.3f} kg",
    )

    print(
        "PROSES SUYU:",
        f"{toplam_parti * PARTI_PROSES_SUYU_KG:.3f} kg",
    )

    print("")
    print(
        "=== HAMMADDE DONEM SONU "
        "STOK KONTROLU ==="
    )

    for row in kutle:
        print(
            f'{row["hammadde"]:<40} '
            f'{row["kalan"]:>10.3f} kg | OK'
        )

    print("")
    print(
        "HAMMADDE DONEM SONU STOK: "
        "0.000 KG"
    )

    print("")
    print(
        "=== EKSIK GERCEK URETIM "
        "VERILERI ==="
    )

    if eksik_alanlar:
        for tarih, alan in eksik_alanlar:
            print(
                "EKSIK:",
                tarih,
                "|",
                alan,
            )

        print("")
        print(
            "AKTARIM DURUMU: BLOKE"
        )

        print(
            "NEDEN: GERCEK URETIM VERISI "
            "EKSIK"
        )

        return False

    print(
        "EKSIK GERCEK URETIM VERISI YOK"
    )

    print("")
    print(
        "AKTARIM DURUMU: HAZIR"
    )

    return True


if __name__ == "__main__":
    hazir = aktarim_on_kontrol()

    if not hazir:
        raise SystemExit(
            "2026 AKTARIMI BASLATILMADI"
        )

    print("")
    print(
        "2026 AKTARIM PREFLIGHT: OK"
    )

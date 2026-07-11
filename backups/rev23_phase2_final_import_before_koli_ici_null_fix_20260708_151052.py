from openpyxl import load_workbook
from pathlib import Path
from shutil import copy2
from datetime import datetime
import sqlite3

from database.db import get_connection
from database.rev23_phase2_preflight import (
    MASTER,
    paketleme_oku,
    sevkiyat_oku,
)
from database.finished_stock_engine import (
    sevkiyat_stok_dus,
)


DB_PATH = Path(
    "/Users/test/Desktop/REDBOX_OS/"
    "database/redbox_os.db"
)

BACKUP_DIR = Path(
    "/Users/test/Desktop/REDBOX_OS/backups"
)



def ambalaj_gram_normalize(value):
    text = str(
        value or ""
    ).strip().lower()

    text = (
        text
        .replace(" ", "")
        .replace(",", ".")
    )

    if text in (
        "500g",
        "0.5kg",
        "0.500kg",
        "500",
    ):
        return 500

    if text in (
        "2.5kg",
        "2.500kg",
        "2500g",
        "2500",
    ):
        return 2500

    raise ValueError(
        "AMBALAJ FORMATI TANINMADI: "
        f"{value!r}"
    )


def paketleme_normalize(
    paketlemeler,
):
    sonuc = []

    for raw in paketlemeler:
        aktifler = []

        paket_500 = int(
            raw.get("paket_500") or 0
        )

        kg_500 = float(
            raw.get("kg_500") or 0
        )

        paket_2500 = int(
            raw.get("paket_2500") or 0
        )

        kg_2500 = float(
            raw.get("kg_2500") or 0
        )

        if paket_500 > 0 or kg_500 > 0:
            if paket_500 <= 0:
                raise ValueError(
                    "500 G PAKET ADEDI GECERSIZ: "
                    f"EXCEL SATIR {raw['satir']}"
                )

            beklenen = (
                paket_500 * 0.500
            )

            if abs(
                beklenen - kg_500
            ) > 0.000001:
                raise ValueError(
                    "500 G PAKET KG UYUSMUYOR: "
                    f"EXCEL SATIR {raw['satir']} | "
                    f"PAKET {paket_500} | "
                    f"KG {kg_500:.3f} | "
                    f"BEKLENEN {beklenen:.3f}"
                )

            aktifler.append({
                "ambalaj_gram": 500,
                "paket_adedi": paket_500,
                "paketlenen_kg": kg_500,
                "koli_ici_adet": None,
            })

        if (
            paket_2500 > 0
            or kg_2500 > 0
        ):
            if paket_2500 <= 0:
                raise ValueError(
                    "2500 G PAKET ADEDI GECERSIZ: "
                    f"EXCEL SATIR {raw['satir']}"
                )

            beklenen = (
                paket_2500 * 2.500
            )

            if abs(
                beklenen - kg_2500
            ) > 0.000001:
                raise ValueError(
                    "2500 G PAKET KG UYUSMUYOR: "
                    f"EXCEL SATIR {raw['satir']} | "
                    f"PAKET {paket_2500} | "
                    f"KG {kg_2500:.3f} | "
                    f"BEKLENEN {beklenen:.3f}"
                )

            aktifler.append({
                "ambalaj_gram": 2500,
                "paket_adedi": paket_2500,
                "paketlenen_kg": kg_2500,
                "koli_ici_adet": None,
            })

        if not aktifler:
            raise ValueError(
                "PAKETLEME AMBALAJ VERISI YOK: "
                f"EXCEL SATIR {raw['satir']}"
            )

        toplam_paketlenen = sum(
            row["paketlenen_kg"]
            for row in aktifler
        )

        net_mamul = float(
            raw["net_mamul_kg"]
        )

        paket_fire = float(
            raw["paketleme_firesi"]
        )

        fark = (
            net_mamul
            - toplam_paketlenen
            - paket_fire
        )

        if abs(fark) > 0.001:
            raise ValueError(
                "PAKETLEME KUTLE DENKLIGI "
                "KAPANMIYOR: "
                f"EXCEL SATIR {raw['satir']} | "
                f"FARK {fark:.3f} KG"
            )

        for index, aktif in enumerate(
            aktifler
        ):
            sonuc.append({
                "satir": raw["satir"],
                "paketleme_tarihi": (
                    raw["paketleme_tarihi"]
                ),
                "uretim_tarihi": (
                    raw["uretim_bagi"]
                ),
                "ambalaj_gram": (
                    aktif["ambalaj_gram"]
                ),
                "paket_adedi": (
                    aktif["paket_adedi"]
                ),
                "koli_ici_adet": (
                    aktif["koli_ici_adet"]
                ),
                "paketlenen_kg": (
                    aktif["paketlenen_kg"]
                ),
                "paketleme_firesi": (
                    paket_fire
                    if index == 0
                    else 0.0
                ),
                "aciklama": (
                    raw.get("aciklama")
                ),
            })

    return sonuc


def sevkiyat_normalize(
    sevkiyatlar,
):
    sonuc = []

    for raw in sevkiyatlar:
        ambalaj_gram = (
            ambalaj_gram_normalize(
                raw["ambalaj"]
            )
        )

        paket_adedi = int(
            raw["paket"]
        )

        sevk_kg = float(
            raw["kg"]
        )

        beklenen_kg = (
            paket_adedi
            * ambalaj_gram
            / 1000
        )

        if abs(
            beklenen_kg - sevk_kg
        ) > 0.001:
            raise ValueError(
                "SEVKIYAT PAKET KG UYUSMUYOR: "
                f"EXCEL SATIR {raw['satir']} | "
                f"PAKET {paket_adedi} | "
                f"AMBALAJ {ambalaj_gram} G | "
                f"KG {sevk_kg:.3f} | "
                f"BEKLENEN {beklenen_kg:.3f}"
            )

        sonuc.append({
            "satir": raw["satir"],
            "sevkiyat_tarihi": (
                raw["sevk_tarihi"]
            ),
            "musteri": raw["alici"],
            "lojistik": raw.get(
                "lojistik"
            ),
            "arac_plaka": raw.get(
                "plaka"
            ),
            "uretim_tarihi": raw.get(
                "uretim_bagi"
            ),
            "ambalaj_gram": (
                ambalaj_gram
            ),
            "paket_adedi": (
                paket_adedi
            ),
            "sevk_kg": sevk_kg,
            "sevk_koli_adedi": 0,
            "sevk_acik_paket_adedi": (
                paket_adedi
            ),
            "belge_no": None,
            "soguk_zincir": 1,
            "aciklama": " | ".join(
                str(value).strip()
                for value in (
                    raw.get("not"),
                    raw.get("lojistik"),
                )
                if value is not None
                and str(value).strip()
            ) or None,
        })

    return sonuc

def tablo_sayisi(conn, tablo):
    return conn.execute(
        f"SELECT COUNT(*) AS sayi FROM {tablo}"
    ).fetchone()["sayi"]


def musteri_getir_veya_olustur(
    conn,
    musteri_adi,
):
    row = conn.execute("""
        SELECT id
        FROM musteriler
        WHERE musteri_adi = ?
    """, (
        musteri_adi,
    )).fetchone()

    if row is not None:
        return row["id"]

    cursor = conn.execute("""
        INSERT INTO musteriler (
            musteri_adi,
            aktif,
            kayit_zamani
        )
        VALUES (?, 1, ?)
    """, (
        musteri_adi,
        datetime.now().strftime(
            "%d.%m.%Y %H:%M:%S"
        ),
    ))

    return cursor.lastrowid


def uretim_map_getir(conn):
    rows = conn.execute("""
        SELECT
            id,
            uretim_tarihi,
            urun_lot_no,
            net_uretim_kg
        FROM uretim
        ORDER BY id
    """).fetchall()

    return {
        row["uretim_tarihi"]: row
        for row in rows
    }


def paketlemeleri_aktar(
    conn,
    paketlemeler,
):
    print("")
    print(
        "=== REV23 PAKETLEME "
        "GERCEK VERI AKTARIMI ==="
    )

    uretim_map = uretim_map_getir(
        conn
    )

    paketleme_map = {}

    for row in paketlemeler:
        uretim_tarihi = row[
            "uretim_tarihi"
        ]

        if uretim_tarihi not in uretim_map:
            raise ValueError(
                "URETIM BULUNAMADI: "
                f"{uretim_tarihi}"
            )

        uretim = uretim_map[
            uretim_tarihi
        ]

        paketlenen_kg = float(
            row["paketlenen_kg"]
        )

        paket_fire = float(
            row["paketleme_firesi"]
        )

        net = float(
            uretim["net_uretim_kg"]
        )

        fark = (
            net
            - paketlenen_kg
            - paket_fire
        )

        if abs(fark) > 0.000001:
            raise ValueError(
                "PAKETLEME KUTLE DENKLIGI "
                "KAPANMADI: "
                f"{uretim_tarihi} | "
                f"FARK {fark:.3f} KG"
            )

        ambalaj_gram = int(
            row["ambalaj_gram"]
        )

        paket_adedi = int(
            row["paket_adedi"]
        )

        koli_ici = int(
            row["koli_ici_adet"]
        )

        cursor = conn.execute("""
            INSERT INTO paketleme (
                paketleme_tarihi,
                uretim_id,
                ambalaj_gram,
                paket_adedi,
                koli_ici_adet,
                paketlenen_kg,
                paketleme_firesi_kg,
                aciklama,
                kayit_zamani
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            row["paketleme_tarihi"],
            uretim["id"],
            ambalaj_gram,
            paket_adedi,
            koli_ici,
            paketlenen_kg,
            paket_fire,
            row.get("aciklama"),
            datetime.now().strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
        ))

        paketleme_id = cursor.lastrowid

        anahtar = (
            uretim_tarihi,
            ambalaj_gram,
        )

        paketleme_map.setdefault(
            anahtar,
            [],
        ).append({
            "paketleme_id": paketleme_id,
            "uretim_id": uretim["id"],
            "urun_lot_no": uretim[
                "urun_lot_no"
            ],
            "paket_adedi": paket_adedi,
            "koli_ici_adet": koli_ici,
        })

        print(
            "OK:",
            row["paketleme_tarihi"],
            "| URETIM:",
            uretim_tarihi,
            "| LOT:",
            uretim["urun_lot_no"],
            "|",
            f"{ambalaj_gram} G",
            "| PAKET:",
            paket_adedi,
            "| KG:",
            f"{paketlenen_kg:.3f}",
            "| FIRE:",
            f"{paket_fire:.3f}",
        )

    return paketleme_map


def sevkiyatlari_aktar(
    conn,
    sevkiyatlar,
):
    print("")
    print(
        "=== REV23 SEVKIYAT "
        "GERCEK VERI AKTARIMI ==="
    )

    uretim_map = uretim_map_getir(
        conn
    )

    for row in sevkiyatlar:
        musteri = str(
            row["musteri"]
        ).strip()

        musteri_id = (
            musteri_getir_veya_olustur(
                conn,
                musteri,
            )
        )

        cursor = conn.execute("""
            INSERT INTO sevkiyat (
                sevkiyat_tarihi,
                sevk_koli_adedi,
                sevk_acik_paket_adedi,
                musteri,
                musteri_id,
                arac_plaka,
                belge_no,
                soguk_zincir,
                aciklama,
                kayit_zamani
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            row["sevkiyat_tarihi"],
            int(
                row.get(
                    "sevk_koli_adedi",
                    0,
                )
            ),
            int(
                row.get(
                    "sevk_acik_paket_adedi",
                    0,
                )
            ),
            musteri,
            musteri_id,
            row.get("arac_plaka"),
            row.get("belge_no"),
            int(
                row.get(
                    "soguk_zincir",
                    1,
                )
            ),
            row.get("aciklama"),
            datetime.now().strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
        ))

        sevkiyat_id = cursor.lastrowid

        ambalaj_gram = int(
            row["ambalaj_gram"]
        )

        toplam_paket = int(
            row["paket_adedi"]
        )

        uretim_tarihleri = row.get(
            "uretim_tarihleri",
            []
        )

        if not uretim_tarihleri:
            raise ValueError(
                "SEVKIYAT URETIM DAGILIMI YOK: "
                f"{row['sevkiyat_tarihi']} | "
                f"{musteri}"
            )

        kalan = toplam_paket

        for uretim_tarihi in uretim_tarihleri:
            if kalan <= 0:
                break

            if uretim_tarihi not in uretim_map:
                raise ValueError(
                    "SEVKIYAT URETIMI BULUNAMADI: "
                    f"{uretim_tarihi}"
                )

            uretim = uretim_map[
                uretim_tarihi
            ]

            stok_rows = conn.execute("""
                SELECT
                    p.id,
                    p.paket_adedi,
                    COALESCE(
                        (
                            SELECT SUM(
                                sk.paket_adedi
                            )
                            FROM sevkiyat_kalemleri sk
                            WHERE
                                sk.paketleme_id = p.id
                        ),
                        0
                    ) AS cikis
                FROM paketleme p
                WHERE p.uretim_id = ?
                  AND p.ambalaj_gram = ?
                ORDER BY p.id
            """, (
                uretim["id"],
                ambalaj_gram,
            )).fetchall()

            mevcut = sum(
                int(stok["paket_adedi"])
                - int(stok["cikis"])
                for stok in stok_rows
            )

            if mevcut <= 0:
                continue

            dusulecek = min(
                mevcut,
                kalan,
            )

            sevkiyat_stok_dus(
                conn,
                sevkiyat_id,
                uretim["id"],
                ambalaj_gram,
                dusulecek,
            )

            kalan -= dusulecek

        if kalan != 0:
            raise ValueError(
                "SEVKIYAT LOT DAGILIMI "
                "TAMAMLANAMADI: "
                f"{row['sevkiyat_tarihi']} | "
                f"{musteri} | "
                f"KALAN {kalan} PAKET"
            )

        sevk_kg = (
            toplam_paket
            * ambalaj_gram
            / 1000
        )

        print(
            "OK:",
            row["sevkiyat_tarihi"],
            "|",
            musteri,
            "|",
            f"{ambalaj_gram} G",
            "| PAKET:",
            toplam_paket,
            "| KG:",
            f"{sevk_kg:.3f}",
        )


def final_dogrula(conn):
    print("")
    print(
        "=== REV23 PHASE 2 "
        "FINAL DOGRULAMA ==="
    )

    for tablo in (
        "paketleme",
        "musteriler",
        "sevkiyat",
        "sevkiyat_kalemleri",
        "mamul_stok_hareketleri",
    ):
        print(
            f"{tablo:30}: "
            f"{tablo_sayisi(conn, tablo)}"
        )

    paket_kg = conn.execute("""
        SELECT COALESCE(
            SUM(paketlenen_kg),
            0
        ) AS toplam
        FROM paketleme
    """).fetchone()["toplam"]

    fire_kg = conn.execute("""
        SELECT COALESCE(
            SUM(paketleme_firesi_kg),
            0
        ) AS toplam
        FROM paketleme
    """).fetchone()["toplam"]

    sevk_kg = conn.execute("""
        SELECT COALESCE(
            SUM(sevk_kg),
            0
        ) AS toplam
        FROM sevkiyat_kalemleri
    """).fetchone()["toplam"]

    kalan_kg = (
        float(paket_kg)
        - float(sevk_kg)
    )

    print("")
    print(
        "TOPLAM PAKETLI:",
        f"{float(paket_kg):.3f} KG",
    )

    print(
        "TOPLAM PAKETLEME FIRESI:",
        f"{float(fire_kg):.3f} KG",
    )

    print(
        "TOPLAM SEVK:",
        f"{float(sevk_kg):.3f} KG",
    )

    print(
        "MAMUL DONEM SONU STOK:",
        f"{kalan_kg:.3f} KG",
    )

    if abs(
        float(paket_kg) - 2362.000
    ) > 0.000001:
        raise ValueError(
            "TOPLAM PAKETLI MAMUL "
            "2362.000 KG DEGIL"
        )

    if abs(
        float(fire_kg) - 7.496
    ) > 0.000001:
        raise ValueError(
            "TOPLAM PAKETLEME FIRESI "
            "7.496 KG DEGIL"
        )

    if abs(
        float(sevk_kg) - 2351.000
    ) > 0.000001:
        raise ValueError(
            "TOPLAM SEVK "
            "2351.000 KG DEGIL"
        )

    if abs(
        kalan_kg - 11.000
    ) > 0.000001:
        raise ValueError(
            "MAMUL DONEM SONU STOK "
            "11.000 KG DEGIL"
        )

    fk = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if fk:
        raise ValueError(
            "FOREIGN KEY CHECK HATALI: "
            f"{fk}"
        )

    print("")
    print(
        "OK: PAKETLI MAMUL "
        "2362.000 KG"
    )

    print(
        "OK: PAKETLEME FIRESI "
        "7.496 KG"
    )

    print(
        "OK: SEVKIYAT "
        "2351.000 KG"
    )

    print(
        "OK: MAMUL STOK "
        "11.000 KG"
    )

    print(
        "OK: FOREIGN KEY CHECK"
    )



MASTER_PATH = Path(
    "/Users/test/Desktop/"
    "REDBOX_MASTER_OPERASYON_SISTEMI_"
    "REV23_LOT_SECIMI_RENKLI_NAV.xlsx"
)


def main():
    if not MASTER_PATH.exists():
        raise FileNotFoundError(
            f"REV23 MASTER EXCEL BULUNAMADI: "
            f"{MASTER_PATH}"
        )

    print("")
    print("REV23 MASTER EXCEL:")
    print(MASTER_PATH)

    wb = load_workbook(
        MASTER_PATH,
        data_only=False,
    )

    print(
        "=== REDBOX OS REV23 PHASE 2 "
        "FINAL GERCEK VERI AKTARIMI ==="
    )

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup = BACKUP_DIR / (
        "redbox_os_before_rev23_phase2_"
        f"{stamp}.db"
    )

    copy2(
        DB_PATH,
        backup,
    )

    print("")
    print(
        "DB BACKUP:",
        backup,
    )

    paketlemeler_raw = (
        paketleme_oku(wb)
    )

    sevkiyatlar_raw = (
        sevkiyat_oku(wb)
    )

    paketlemeler = (
        paketleme_normalize(
            paketlemeler_raw
        )
    )

    sevkiyatlar = (
        sevkiyat_normalize(
            sevkiyatlar_raw
        )
    )

    print("")
    print(
        "=== REV23 NORMALIZASYON ==="
    )

    print(
        "HAM PAKETLEME SATIRI:",
        len(paketlemeler_raw),
    )

    print(
        "SQL PAKETLEME SATIRI:",
        len(paketlemeler),
    )

    print(
        "HAM SEVKIYAT SATIRI:",
        len(sevkiyatlar_raw),
    )

    print(
        "SQL SEVKIYAT SATIRI:",
        len(sevkiyatlar),
    )

    print(
        "NORMALIZE PAKETLEME KG:",
        f"{sum(row['paketlenen_kg'] for row in paketlemeler):.3f}",
    )

    print(
        "NORMALIZE PAKETLEME FIRE:",
        f"{sum(row['paketleme_firesi'] for row in paketlemeler):.3f}",
    )

    print(
        "NORMALIZE SEVKIYAT KG:",
        f"{sum(row['sevk_kg'] for row in sevkiyatlar):.3f}",
    )

    conn = get_connection()

    try:
        conn.execute("BEGIN")

        print("")
        print(
            "=== PHASE 2 BOSLUK "
            "KONTROLU ==="
        )

        for tablo in (
            "paketleme",
            "sevkiyat",
            "sevkiyat_kalemleri",
            "mamul_stok_hareketleri",
        ):
            sayi = tablo_sayisi(
                conn,
                tablo,
            )

            print(
                f"{tablo:30}: {sayi}"
            )

            if sayi != 0:
                raise ValueError(
                    "PHASE 2 TABLOSU BOS DEGIL: "
                    f"{tablo} = {sayi}"
                )

        paketlemeleri_aktar(
            conn,
            paketlemeler,
        )

        sevkiyatlari_aktar(
            conn,
            sevkiyatlar,
        )

        final_dogrula(
            conn
        )

        conn.commit()

        print("")
        print(
            "TRANSACTION COMMIT: OK"
        )

    except Exception as hata:
        conn.rollback()

        print("")
        print(
            "TRANSACTION ROLLBACK: OK"
        )

        print(
            "HATA:",
            hata,
        )

        raise

    finally:
        conn.close()

    print("")
    print(
        "REV23 TABANLI 2026 "
        "PAKETLEME + SEVKIYAT + "
        "MAMUL STOK AKTARIMI BASARILI"
    )


if __name__ == "__main__":
    main()

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


def main():
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

    paketlemeler = (
        paketleme_oku()
    )

    sevkiyatlar = (
        sevkiyat_oku()
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

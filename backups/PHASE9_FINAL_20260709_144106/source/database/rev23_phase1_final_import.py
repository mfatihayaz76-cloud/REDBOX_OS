from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import shutil

from openpyxl import load_workbook

from database.db import get_connection
from database.import_2026_rev23 import (
    excel_bul,
    uretimleri_oku,
    lot_baglarini_oku,
)
from database.rev23_phase1_preflight import (
    aktif_recete_oku,
    excel_depo_lotlarini_oku,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "redbox_os.db"
BACKUP_DIR = BASE_DIR / "backups"

TARIHSEL_TAVUK_LOT = (
    "TARIHSEL-LOT-BILGISI-YOK-TAVUK-CESNISI"
)


def tarih_parse(value):
    return datetime.strptime(
        value,
        "%d.%m.%Y",
    )


def tarih_format(value):
    return value.strftime(
        "%d.%m.%Y"
    )


def tedarikci_kart(conn, ad):
    row = conn.execute("""
        SELECT id
        FROM tedarikciler
        WHERE tedarikci_adi = ?
    """, (ad,)).fetchone()

    if row:
        return row["id"]

    cursor = conn.execute("""
        INSERT INTO tedarikciler (
            tedarikci_adi,
            aktif,
            kayit_zamani
        )
        VALUES (?, 1, ?)
    """, (
        ad,
        datetime.now().strftime(
            "%d.%m.%Y %H:%M:%S"
        ),
    ))

    return cursor.lastrowid


def hammadde_map_getir(conn):
    rows = conn.execute("""
        SELECT id, ad
        FROM hammaddeler
        WHERE aktif = 1
    """).fetchall()

    return {
        row["ad"]: row["id"]
        for row in rows
    }


def operasyon_temizle(conn):
    print("")
    print(
        "=== MEVCUT HATALI PHASE 1 "
        "VERISI TEMIZLENIYOR ==="
    )

    tablolar = [
        "uretim_hammadde_lotlari",
        "uretim_recete",
        "uretim",
        "depo_kabul",
    ]

    for tablo in tablolar:
        once = conn.execute(
            f"SELECT COUNT(*) AS sayi FROM {tablo}"
        ).fetchone()["sayi"]

        conn.execute(
            f"DELETE FROM {tablo}"
        )

        print(
            "TEMIZLENDI:",
            tablo,
            "|",
            once,
            "KAYIT",
        )


def lot_ihtiyaclarini_hesapla(
    uretimler,
    lot_baglari,
    recete_kalemleri,
):
    recete_map = {
        row["hammadde"]:
        float(row["miktar_kg"])
        for row in recete_kalemleri
    }

    lot_ihtiyaclari = defaultdict(float)
    ilk_kullanim = {}

    for uretim in uretimler:
        tarih = uretim["uretim_tarihi"]
        parti = uretim["parti_sayisi"]

        baglar = lot_baglari[
            tarih
        ]["baglar"]

        for hammadde, parti_kg in recete_map.items():
            lot_no = baglar.get(
                hammadde
            )

            if (
                hammadde == "Tavuk Çeşnisi"
                and not lot_no
            ):
                lot_no = TARIHSEL_TAVUK_LOT

            if not lot_no:
                raise ValueError(
                    "URETIM LOT BAGI EKSIK: "
                    f"{tarih} | {hammadde}"
                )

            key = (
                hammadde,
                lot_no,
            )

            lot_ihtiyaclari[key] += (
                parti_kg * parti
            )

            kullanim_tarihi = tarih_parse(
                tarih
            )

            if (
                key not in ilk_kullanim
                or kullanim_tarihi
                < ilk_kullanim[key]
            ):
                ilk_kullanim[
                    key
                ] = kullanim_tarihi

    return (
        lot_ihtiyaclari,
        ilk_kullanim,
    )


def depo_kabulleri_olustur(
    conn,
    hammadde_map,
    depo_lotlari,
    lot_ihtiyaclari,
    ilk_kullanim,
):
    print("")
    print(
        "=== REV23 LOT BAZLI "
        "DEPO KABUL AKTARIMI ==="
    )

    depo_id_map = {}

    for key, miktar in sorted(
        lot_ihtiyaclari.items()
    ):
        hammadde, lot_no = key

        excel_row = depo_lotlari.get(
            key
        )

        if lot_no == TARIHSEL_TAVUK_LOT:
            tedarikci = "Ankara Gıda"
            kabul_tarihi = tarih_format(
                ilk_kullanim[key]
                - timedelta(days=1)
            )
            uretim_tarihi = None
            skt_tett = None
            durum = "KABUL"
            aciklama = (
                "TARİHSEL KAYIT: 14.01.2026 ve "
                "17.02.2026 üretimlerinde kullanılan "
                "Tavuk Çeşnisi gerçek tedarikçi lot "
                "numarası REV23 kayıtlarında mevcut "
                "değildir. Bu kod sistemsel izlenebilirlik "
                "için oluşturulmuş tarihsel eksik-lot "
                "tanımlayıcısıdır; gerçek tedarikçi lotu "
                "değildir."
            )
        else:
            if excel_row is None:
                raise ValueError(
                    "REV23 DEPO LOT KARTI YOK: "
                    f"{hammadde} | {lot_no}"
                )

            tedarikci = (
                excel_row["tedarikci"]
                or "TEDARIKCI BILGISI YOK"
            )

            kabul_tarihi = (
                excel_row["kabul_tarihi"]
                if excel_row["kabul_tarihi"]
                else tarih_format(
                    ilk_kullanim[key]
                    - timedelta(days=1)
                )
            )

            uretim_tarihi = (
                excel_row["uretim_tarihi"]
            )

            skt_tett = (
                excel_row["skt_tett"]
            )

            durum = "KABUL"

            aciklama_parcalari = []

            if excel_row["aciklama"]:
                aciklama_parcalari.append(
                    excel_row["aciklama"]
                )

            if not excel_row["kabul_tarihi"]:
                aciklama_parcalari.append(
                    "Tarihsel aktarım: kesin giriş/alım "
                    "tarihi mevcut kayıtta bulunmadığı "
                    "için lotun ilk üretim kullanımından "
                    "bir gün önce sistemsel kabul tarihi "
                    "olarak atanmıştır."
                )

            aciklama = (
                " | ".join(aciklama_parcalari)
                if aciklama_parcalari
                else None
            )

        tedarikci_id = tedarikci_kart(
            conn,
            tedarikci,
        )

        cursor = conn.execute("""
            INSERT INTO depo_kabul (
                kabul_tarihi,
                hammadde_id,
                tedarikci,
                tedarikci_lot_no,
                uretim_tarihi,
                skt_tett,
                miktar_kg,
                kabul_durumu,
                aciklama,
                kayit_zamani,
                tedarikci_id
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )
        """, (
            kabul_tarihi,
            hammadde_map[hammadde],
            tedarikci,
            lot_no,
            uretim_tarihi,
            skt_tett,
            float(miktar),
            durum,
            aciklama,
            datetime.now().strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
            tedarikci_id,
        ))

        depo_id_map[key] = (
            cursor.lastrowid
        )

        print(
            "OK:",
            kabul_tarihi,
            "|",
            hammadde,
            "| LOT:",
            lot_no,
            "|",
            f"{miktar:.3f} kg",
        )

    return depo_id_map


def uretimleri_olustur(
    conn,
    uretimler,
    lot_baglari,
    recete,
    recete_kalemleri,
    depo_id_map,
):
    print("")
    print(
        "=== REV23 11 URETIM VE "
        "GERCEK LOT BAGI AKTARIMI ==="
    )

    recete_map = {
        row["hammadde"]:
        float(row["miktar_kg"])
        for row in recete_kalemleri
    }

    for row in uretimler:
        cursor = conn.execute("""
            INSERT INTO uretim (
                uretim_tarihi,
                urun_lot_no,
                parti_sayisi,
                teorik_uretim_kg,
                uretim_firesi_kg,
                net_uretim_kg,
                personel_1,
                personel_2,
                aciklama,
                kayit_zamani
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )
        """, (
            row["uretim_tarihi"],
            row["urun_lot_no"],
            row["parti_sayisi"],
            row["teorik_uretim_kg"],
            row["uretim_firesi_kg"],
            row["net_uretim_kg"],
            "Fatih Ayaz",
            "Eda Ayaz",
            row["aciklama"],
            datetime.now().strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
        ))

        uretim_id = cursor.lastrowid

        conn.execute("""
            INSERT INTO uretim_recete (
                uretim_id,
                recete_id
            )
            VALUES (?, ?)
        """, (
            uretim_id,
            recete["id"],
        ))

        baglar = lot_baglari[
            row["uretim_tarihi"]
        ]["baglar"]

        bag_sayisi = 0

        for hammadde, parti_kg in recete_map.items():
            lot_no = baglar.get(
                hammadde
            )

            if (
                hammadde == "Tavuk Çeşnisi"
                and not lot_no
            ):
                lot_no = TARIHSEL_TAVUK_LOT

            key = (
                hammadde,
                lot_no,
            )

            kullanilan = (
                parti_kg
                * row["parti_sayisi"]
            )

            conn.execute("""
                INSERT INTO uretim_hammadde_lotlari (
                    uretim_id,
                    depo_kabul_id,
                    kullanilan_miktar_kg
                )
                VALUES (?, ?, ?)
            """, (
                uretim_id,
                depo_id_map[key],
                kullanilan,
            ))

            bag_sayisi += 1

        print(
            "OK:",
            row["uretim_tarihi"],
            "| LOT:",
            row["urun_lot_no"],
            "| PARTI:",
            row["parti_sayisi"],
            "| FIRE:",
            f'{row["uretim_firesi_kg"]:.3f}',
            "| NET:",
            f'{row["net_uretim_kg"]:.3f}',
            "| HAMMADDE LOT BAG:",
            bag_sayisi,
        )


def final_dogrula(conn):
    print("")
    print(
        "=== REV23 PHASE 1 FINAL DOGRULAMA ==="
    )

    beklenen = {
        "uretim": 11,
        "uretim_recete": 11,
        "uretim_hammadde_lotlari": 88,
    }

    for tablo, beklenen_sayi in beklenen.items():
        sayi = conn.execute(
            f"SELECT COUNT(*) AS sayi FROM {tablo}"
        ).fetchone()["sayi"]

        print(
            f"{tablo:<30}: {sayi}"
        )

        if sayi != beklenen_sayi:
            raise ValueError(
                f"{tablo} KAYIT SAYISI HATALI: "
                f"{sayi} / {beklenen_sayi}"
            )

    print("")
    print(
        "=== HAMMADDE DONEM SONU STOK ==="
    )

    rows = conn.execute("""
        SELECT
            h.ad AS hammadde,
            SUM(dk.miktar_kg) AS giris_kg,
            COALESCE(
                (
                    SELECT SUM(
                        uhl.kullanilan_miktar_kg
                    )
                    FROM uretim_hammadde_lotlari uhl
                    JOIN depo_kabul dk2
                      ON dk2.id = uhl.depo_kabul_id
                    WHERE dk2.hammadde_id = h.id
                ),
                0
            ) AS tuketim_kg
        FROM hammaddeler h
        JOIN depo_kabul dk
          ON dk.hammadde_id = h.id
        GROUP BY
            h.id,
            h.ad
        ORDER BY h.id
    """).fetchall()

    toplam_kalan = 0.0

    for row in rows:
        kalan = (
            float(row["giris_kg"])
            - float(row["tuketim_kg"])
        )

        if abs(kalan) < 0.000001:
            kalan = 0.0

        toplam_kalan += kalan

        print(
            f'{row["hammadde"]:<45}'
            f'{kalan:>12.3f} kg'
        )

    if abs(toplam_kalan) > 0.000001:
        raise ValueError(
            "HAMMADDE DONEM SONU STOK "
            f"0 DEGIL: {toplam_kalan:.6f} KG"
        )

    print("")
    print(
        "OK: HAMMADDE DONEM SONU "
        "STOK 0.000 KG"
    )

    row_0705 = conn.execute("""
        SELECT
            uretim_firesi_kg,
            net_uretim_kg
        FROM uretim
        WHERE uretim_tarihi = '07.05.2026'
    """).fetchone()

    if (
        row_0705 is None
        or abs(
            float(
                row_0705["uretim_firesi_kg"]
            ) - 3.0
        ) > 0.000001
    ):
        raise ValueError(
            "07.05.2026 FIRE FINAL "
            "DOGRULAMASI HATALI"
        )

    print(
        "OK: 07.05.2026 FIRE 3.000 KG"
    )

    row_1504 = conn.execute("""
        SELECT net_uretim_kg
        FROM uretim
        WHERE uretim_tarihi = '15.04.2026'
    """).fetchone()

    if (
        row_1504 is None
        or abs(
            float(
                row_1504["net_uretim_kg"]
            ) - 260.0
        ) > 0.000001
    ):
        raise ValueError(
            "15.04.2026 NET 260 KG "
            "DOGRULAMASI HATALI"
        )

    print(
        "OK: 15.04.2026 NET 260.000 KG"
    )

    benecel = conn.execute("""
        SELECT COUNT(*) AS sayi
        FROM depo_kabul dk
        JOIN hammaddeler h
          ON h.id = dk.hammadde_id
        WHERE h.ad =
            'Metilselüloz Benecel A4M E461'
          AND dk.tedarikci_lot_no = '2743063'
    """).fetchone()["sayi"]

    if benecel != 1:
        raise ValueError(
            "BENECEL 2743063 LOT "
            "DOGRULAMASI HATALI"
        )

    print(
        "OK: BENECEL LOT 2743063"
    )

    fk = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if fk:
        raise ValueError(
            "FOREIGN KEY CHECK HATALI: "
            + str(fk)
        )

    print(
        "OK: FOREIGN KEY CHECK"
    )


def main():
    print(
        "=== REDBOX OS REV23 PHASE 1 "
        "FINAL GERCEK VERI AKTARIMI ==="
    )

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_path = (
        BACKUP_DIR
        / f"redbox_os_before_rev23_final_{stamp}.db"
    )

    shutil.copy2(
        DB_PATH,
        backup_path,
    )

    print("")
    print(
        "DB BACKUP:",
        backup_path,
    )

    excel_path = excel_bul()

    wb = load_workbook(
        excel_path,
        data_only=False,
    )

    uretimler = uretimleri_oku(
        wb
    )

    lot_baglari = lot_baglarini_oku(
        wb
    )

    depo_lotlari = excel_depo_lotlarini_oku(
        wb
    )

    conn = get_connection()

    try:
        conn.execute("BEGIN")

        recete, recete_kalemleri = (
            aktif_recete_oku(conn)
        )

        hammadde_map = (
            hammadde_map_getir(conn)
        )

        lot_ihtiyaclari, ilk_kullanim = (
            lot_ihtiyaclarini_hesapla(
                uretimler,
                lot_baglari,
                recete_kalemleri,
            )
        )

        operasyon_temizle(
            conn
        )

        depo_id_map = (
            depo_kabulleri_olustur(
                conn,
                hammadde_map,
                depo_lotlari,
                lot_ihtiyaclari,
                ilk_kullanim,
            )
        )

        uretimleri_olustur(
            conn,
            uretimler,
            lot_baglari,
            recete,
            recete_kalemleri,
            depo_id_map,
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
        "REV23 TABANLI 2026 DEPO KABUL + "
        "11 URETIM + LOT IZLENEBILIRLIK "
        "AKTARIMI BASARILI"
    )


if __name__ == "__main__":
    main()

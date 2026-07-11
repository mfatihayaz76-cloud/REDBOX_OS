import shutil
from datetime import datetime
from pathlib import Path

from database.db import get_connection
from database.import_2026_data import URETIMLER_2026
from database.import_2026_depo_data import DEPO_KABULLER_2026
from database.import_2026_engine import aktarim_on_kontrol
from database.stock_engine import uretim_stok_isle


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "redbox_os.db"
BACKUP_DIR = BASE_DIR / "backups"


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


def aktif_recete_getir(conn):
    row = conn.execute("""
        SELECT
            id,
            ad,
            parti_teorik_kg
        FROM receteler
        WHERE aktif = 1
        ORDER BY id
        LIMIT 1
    """).fetchone()

    if row is None:
        raise ValueError(
            "Aktif reçete bulunamadı."
        )

    return row


def tedarikci_kart_getir_veya_olustur(
    conn,
    tedarikci_adi,
):
    tedarikci_adi = str(
        tedarikci_adi or ""
    ).strip()

    if not tedarikci_adi:
        return None

    row = conn.execute("""
        SELECT id
        FROM tedarikciler
        WHERE tedarikci_adi = ?
    """, (
        tedarikci_adi,
    )).fetchone()

    if row is not None:
        return row["id"]

    cursor = conn.execute("""
        INSERT INTO tedarikciler (
            tedarikci_adi,
            aktif,
            kayit_zamani
        )
        VALUES (?, 1, ?)
    """, (
        tedarikci_adi,
        datetime.now().strftime(
            "%d.%m.%Y %H:%M:%S"
        ),
    ))

    return cursor.lastrowid


def operasyon_tablolari_bos_dogrula(conn):
    tablolar = (
        "depo_kabul",
        "uretim",
        "uretim_recete",
        "uretim_hammadde_lotlari",
        "paketleme",
        "sevkiyat",
        "sevkiyat_kalemleri",
    )

    dolu = []

    for tablo in tablolar:
        sayi = conn.execute(
            f"SELECT COUNT(*) AS sayi FROM {tablo}"
        ).fetchone()["sayi"]

        print(
            f"{tablo:<30}:",
            sayi,
        )

        if sayi != 0:
            dolu.append(
                f"{tablo}={sayi}"
            )

    if dolu:
        raise ValueError(
            "Operasyon tabloları boş değil. "
            "Aktarım durduruldu: "
            + ", ".join(dolu)
        )


def depo_kabulleri_aktar(
    conn,
    hammadde_map,
):
    print("")
    print(
        "=== DEPO KABUL AKTARIMI ==="
    )

    for row in DEPO_KABULLER_2026:
        hammadde = row["hammadde"]

        if hammadde not in hammadde_map:
            raise ValueError(
                "Aktif hammadde bulunamadı: "
                f"{hammadde}"
            )

        tedarikci = str(
            row.get("tedarikci") or ""
        ).strip()

        tedarikci_id = (
            tedarikci_kart_getir_veya_olustur(
                conn,
                tedarikci,
            )
        )

        conn.execute("""
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
            row["kabul_tarihi"],
            hammadde_map[hammadde],
            tedarikci or None,
            row["tedarikci_lot_no"],
            row.get("uretim_tarihi"),
            row.get("skt_tett"),
            float(row["miktar_kg"]),
            row.get(
                "kabul_durumu",
                "UYGUN",
            ),
            row.get("aciklama"),
            datetime.now().strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
            tedarikci_id,
        ))

        print(
            "OK:",
            hammadde,
            "|",
            row["tedarikci_lot_no"],
            "|",
            f'{float(row["miktar_kg"]):.3f} kg',
        )


def uretimleri_aktar(
    conn,
    recete,
):
    print("")
    print(
        "=== URETIM VE FIFO AKTARIMI ==="
    )

    for row in URETIMLER_2026:
        parti = int(
            row["parti_sayisi"]
        )

        fire = float(
            row["uretim_firesi_kg"]
        )

        teorik = round(
            parti
            * float(recete["parti_teorik_kg"]),
            3,
        )

        net = round(
            teorik - fire,
            3,
        )

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
            parti,
            teorik,
            fire,
            net,
            "Fatih Ayaz",
            "Eda Ayaz",
            row.get("aciklama"),
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

        uretim_stok_isle(
            conn,
            uretim_id,
            parti,
        )

        lot_sayisi = conn.execute("""
            SELECT COUNT(*) AS sayi
            FROM uretim_hammadde_lotlari
            WHERE uretim_id = ?
        """, (
            uretim_id,
        )).fetchone()["sayi"]

        print(
            "OK:",
            row["uretim_tarihi"],
            "| LOT:",
            row["urun_lot_no"],
            "| PARTI:",
            parti,
            "| FIRE:",
            f"{fire:.3f}",
            "| NET:",
            f"{net:.3f}",
            "| HAMMADDE LOT BAG:",
            lot_sayisi,
        )


def final_dogrula(conn):
    print("")
    print(
        "=== PHASE 1 FINAL DOGRULAMA ==="
    )

    sayilar = {}

    for tablo in (
        "depo_kabul",
        "uretim",
        "uretim_recete",
        "uretim_hammadde_lotlari",
    ):
        sayi = conn.execute(
            f"SELECT COUNT(*) AS sayi FROM {tablo}"
        ).fetchone()["sayi"]

        sayilar[tablo] = sayi

        print(
            f"{tablo:<30}:",
            sayi,
        )

    if sayilar["depo_kabul"] != len(
        DEPO_KABULLER_2026
    ):
        raise ValueError(
            "Depo kabul kayıt sayısı uyuşmuyor."
        )

    if sayilar["uretim"] != len(
        URETIMLER_2026
    ):
        raise ValueError(
            "Üretim kayıt sayısı uyuşmuyor."
        )

    if sayilar["uretim_recete"] != len(
        URETIMLER_2026
    ):
        raise ValueError(
            "Üretim reçete bağlantısı uyuşmuyor."
        )

    if (
        sayilar["uretim_hammadde_lotlari"]
        <= 0
    ):
        raise ValueError(
            "Hammadde lot tüketim bağlantısı yok."
        )

    print("")
    print(
        "=== HAMMADDE KALAN STOK ==="
    )

    stoklar = conn.execute("""
        SELECT
            h.ad AS hammadde,
            ROUND(
                SUM(d.miktar_kg)
                - COALESCE((
                    SELECT SUM(
                        uhl.kullanilan_miktar_kg
                    )
                    FROM uretim_hammadde_lotlari uhl
                    JOIN depo_kabul dx
                      ON dx.id = uhl.depo_kabul_id
                    WHERE dx.hammadde_id = h.id
                ), 0),
                3
            ) AS kalan_kg
        FROM hammaddeler h
        JOIN depo_kabul d
          ON d.hammadde_id = h.id
        WHERE h.aktif = 1
        GROUP BY
            h.id,
            h.ad
        ORDER BY h.id
    """).fetchall()

    for row in stoklar:
        print(
            f'{row["hammadde"]:<40} '
            f'{float(row["kalan_kg"]):>10.3f} kg'
        )

        if abs(
            float(row["kalan_kg"])
        ) > 0.001:
            raise ValueError(
                "Hammadde dönem sonu stok "
                "sıfır değil: "
                f'{row["hammadde"]} '
                f'{row["kalan_kg"]} kg'
            )

    fk = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if fk:
        for row in fk:
            print(
                dict(row)
            )

        raise ValueError(
            "FOREIGN KEY CHECK HATASI"
        )

    print("")
    print(
        "OK: HAMMADDE DONEM SONU STOK 0.000 KG"
    )

    print(
        "OK: FOREIGN KEY CHECK"
    )


def main():
    print(
        "=== REDBOX OS 2026 PHASE 1 "
        "GERCEK VERI AKTARIMI ==="
    )

    if not aktarim_on_kontrol():
        raise SystemExit(
            "HATA: PREFLIGHT BASARISIZ"
        )

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    zaman = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup = (
        BACKUP_DIR
        / f"redbox_os_before_2026_import_{zaman}.db"
    )

    shutil.copy2(
        DB_PATH,
        backup,
    )

    print("")
    print(
        "DB BACKUP:",
        backup,
    )

    conn = get_connection()

    try:
        print("")
        print(
            "=== OPERASYON TABLOLARI "
            "BOSLUK KONTROLU ==="
        )

        operasyon_tablolari_bos_dogrula(
            conn
        )

        hammadde_map = (
            hammadde_map_getir(
                conn
            )
        )

        recete = aktif_recete_getir(
            conn
        )

        conn.execute(
            "BEGIN IMMEDIATE"
        )

        depo_kabulleri_aktar(
            conn,
            hammadde_map,
        )

        uretimleri_aktar(
            conn,
            recete,
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
            str(hata),
        )

        raise

    finally:
        conn.close()

    print("")
    print(
        "2026 DEPO KABUL + URETIM + FIFO "
        "GERCEK VERI AKTARIMI BASARILI"
    )


if __name__ == "__main__":
    main()

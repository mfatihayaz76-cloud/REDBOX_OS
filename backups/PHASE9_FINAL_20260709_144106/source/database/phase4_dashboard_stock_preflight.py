from pathlib import Path
import sqlite3
import ast

ROOT = Path.home() / "Desktop" / "REDBOX_OS"
APP = ROOT / "app.py"
DB = ROOT / "database" / "redbox_os.db"
ENGINE = ROOT / "database" / "finished_stock_engine.py"

print("")
print("=== REDBOX OS PHASE 4 DASHBOARD + STOK PREFLIGHT ===")

for path in [APP, DB, ENGINE]:
    print(
        path.name,
        ":",
        "VAR" if path.exists() else "YOK"
    )

if not APP.exists():
    raise RuntimeError("APP.PY BULUNAMADI")

if not DB.exists():
    raise RuntimeError("DATABASE BULUNAMADI")

if not ENGINE.exists():
    raise RuntimeError(
        "FINISHED STOCK ENGINE BULUNAMADI"
    )

app_text = APP.read_text(encoding="utf-8")
engine_text = ENGINE.read_text(encoding="utf-8")

ast.parse(app_text)
ast.parse(engine_text)

print("")
print("OK: APP.PY AST")
print("OK: FINISHED STOCK ENGINE AST")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

try:
    print("")
    print("=== CANLI KPI SOZLESMESI ===")

    net_uretim = float(
        conn.execute("""
            SELECT COALESCE(
                SUM(net_uretim_kg),
                0
            )
            FROM uretim
        """).fetchone()[0]
    )

    paketli = float(
        conn.execute("""
            SELECT COALESCE(
                SUM(paketlenen_kg),
                0
            )
            FROM paketleme
        """).fetchone()[0]
    )

    paket_fire = float(
        conn.execute("""
            SELECT COALESCE(
                SUM(paketleme_firesi_kg),
                0
            )
            FROM paketleme
        """).fetchone()[0]
    )

    sevk = float(
        conn.execute("""
            SELECT COALESCE(
                SUM(sevk_kg),
                0
            )
            FROM sevkiyat_kalemleri
        """).fetchone()[0]
    )

    mamul_stok = paketli - sevk

    print(
        "NET URETIM:",
        f"{net_uretim:.3f}",
        "KG"
    )

    print(
        "PAKETLI:",
        f"{paketli:.3f}",
        "KG"
    )

    print(
        "PAKETLEME FIRESI:",
        f"{paket_fire:.3f}",
        "KG"
    )

    print(
        "SEVK:",
        f"{sevk:.3f}",
        "KG"
    )

    print(
        "MAMUL STOK:",
        f"{mamul_stok:.3f}",
        "KG"
    )

    if abs(net_uretim - 2369.496) >= 0.000001:
        raise RuntimeError(
            "NET URETIM KPI SOZLESMESI BOZUK"
        )

    if abs(paketli - 2362.000) >= 0.000001:
        raise RuntimeError(
            "PAKETLI KPI SOZLESMESI BOZUK"
        )

    if abs(paket_fire - 7.496) >= 0.000001:
        raise RuntimeError(
            "PAKETLEME FIRESI KPI SOZLESMESI BOZUK"
        )

    if abs(sevk - 2352.000) >= 0.000001:
        raise RuntimeError(
            "SEVK KPI SOZLESMESI BOZUK"
        )

    if abs(mamul_stok - 10.000) >= 0.000001:
        raise RuntimeError(
            "MAMUL STOK KPI SOZLESMESI BOZUK"
        )

    print("")
    print("OK: CANLI KPI SOZLESMESI KAPALI")

    print("")
    print("=== LOT BAZLI CANLI MAMUL STOK ===")

    rows = conn.execute("""
        SELECT
            u.id AS uretim_id,
            u.uretim_tarihi,
            u.urun_lot_no,
            p.ambalaj_gram,
            p.koli_ici_adet,
            SUM(p.paket_adedi) AS paketlenen_paket,
            COALESCE(
                (
                    SELECT SUM(
                        sk.paket_adedi
                    )
                    FROM sevkiyat_kalemleri sk
                    JOIN paketleme px
                      ON px.id = sk.paketleme_id
                    WHERE px.uretim_id = u.id
                      AND px.ambalaj_gram =
                          p.ambalaj_gram
                ),
                0
            ) AS sevk_paket
        FROM paketleme p
        JOIN uretim u
          ON u.id = p.uretim_id
        GROUP BY
            u.id,
            u.uretim_tarihi,
            u.urun_lot_no,
            p.ambalaj_gram,
            p.koli_ici_adet
        ORDER BY
            u.id,
            p.ambalaj_gram
    """).fetchall()

    aktif_stok = []

    for row in rows:
        kalan = (
            int(row["paketlenen_paket"])
            - int(row["sevk_paket"])
        )

        kalan_kg = (
            kalan
            * int(row["ambalaj_gram"])
            / 1000
        )

        if kalan > 0:
            aktif_stok.append(
                {
                    "uretim_tarihi":
                        row["uretim_tarihi"],
                    "urun_lot_no":
                        row["urun_lot_no"],
                    "ambalaj_gram":
                        int(row["ambalaj_gram"]),
                    "kalan_paket":
                        kalan,
                    "kalan_kg":
                        kalan_kg,
                }
            )

            print(
                row["uretim_tarihi"],
                "| LOT:",
                row["urun_lot_no"],
                "|",
                row["ambalaj_gram"],
                "G | PAKET:",
                kalan,
                "| KG:",
                f"{kalan_kg:.3f}"
            )

    if len(aktif_stok) != 1:
        raise RuntimeError(
            "AKTIF MAMUL STOK LOT SAYISI "
            f"1 DEGIL: {len(aktif_stok)}"
        )

    stok = aktif_stok[0]

    if stok["urun_lot_no"] != "270623":
        raise RuntimeError(
            "FINAL STOK LOTU 270623 DEGIL"
        )

    if stok["ambalaj_gram"] != 500:
        raise RuntimeError(
            "FINAL STOK AMBALAJI 500 G DEGIL"
        )

    if stok["kalan_paket"] != 20:
        raise RuntimeError(
            "FINAL STOK 20 PAKET DEGIL"
        )

    if abs(stok["kalan_kg"] - 10.000) >= 0.000001:
        raise RuntimeError(
            "FINAL STOK 10 KG DEGIL"
        )

    print("")
    print(
        "OK: FINAL STOK "
        "270623 | 500 G | 20 PAKET | 10.000 KG"
    )

    print("")
    print("=== APP ENTEGRASYON SOZLESMESI ===")

    kontroller = {
        "MAMUL STOK IMPORT":
            "mamul_stok_ozeti" in app_text,

        "AMBALAJ STOK IMPORT":
            "ambalaj_stok_toplami" in app_text,

        "SEVKIYAT STOK DUS":
            "sevkiyat_stok_dus" in app_text,

        "ANA SAYFA":
            "def ana_sayfa(self):" in app_text,

        "MAMUL DEPO STOKU":
            '"MAMUL DEPO STOKU"' in app_text,

        "2026 NET URETIM":
            '"2026 NET ÜRETİM"' in app_text,

        "2026 SEVKIYAT":
            '"2026 SEVKİYAT"' in app_text,

        "STOK MENU YOK":
            '("STOK", self.stok)' not in app_text,

        "STOK FONKSIYONU YOK":
            "def stok(self):" not in app_text,
    }

    for ad, sonuc in kontroller.items():
        print(
            ("OK: " if sonuc else "HATA: ")
            + ad
        )

    if not all(kontroller.values()):
        raise RuntimeError(
            "APP ENTEGRASYON SOZLESMESI "
            "BEKLENENDEN FARKLI"
        )

    print("")
    print(
        "OK: MEVCUT MAMUL STOK MOTORU "
        "UYGULAMAYA BAGLI"
    )

    print(
        "OK: AYRI STOK EKRANI HENUZ YOK"
    )

    print("")
    print("=== PHASE 4 PREFLIGHT FINAL ===")

    print(
        "OK: NET URETIM 2369.496 KG"
    )

    print(
        "OK: PAKETLI 2362.000 KG"
    )

    print(
        "OK: PAKETLEME FIRESI 7.496 KG"
    )

    print(
        "OK: SEVK 2352.000 KG"
    )

    print(
        "OK: MAMUL STOK 10.000 KG"
    )

    print(
        "OK: FINAL LOT 270623"
    )

    print(
        "OK: FINAL STOK 20 x 500 G"
    )

finally:
    conn.close()

print("")
print(
    "PHASE 4 DASHBOARD + STOK PREFLIGHT BASARILI"
)

print("")
print("NOT: APP.PY DEGISTIRILMEDI")
print("NOT: SQL DEGISTIRILMEDI")
print("NOT: EXCEL DEGISTIRILMEDI")

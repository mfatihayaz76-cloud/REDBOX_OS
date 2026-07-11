import hashlib
import shutil
import sqlite3
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

LIVE_DB = (
    ROOT
    / "database"
    / "redbox_os.db"
)

PROTECTED = [
    LIVE_DB,
    ROOT / "app.py",
    ROOT / "database" / "db.py",
    ROOT / "database" / "stock_engine.py",
    ROOT / "database" / "raw_material_stock_engine.py",
    ROOT / "database" / "finished_stock_engine.py",
    ROOT / "database" / "report_engine.py",
    ROOT / "tests" / "test_phase9_baseline.py",
    ROOT / "tests" / "test_business_rules_sandbox.py",
    ROOT / "tests" / "phase12_p0_sandbox_proof.py",
]


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def historical_digest(conn):
    rows = conn.execute("""
        SELECT
            id,
            uretim_id,
            depo_kabul_id,
            kullanilan_miktar_kg
        FROM uretim_hammadde_lotlari
        ORDER BY id
    """).fetchall()

    h = hashlib.sha256()

    for row in rows:
        h.update(
            repr(tuple(row)).encode("utf-8")
        )

    return h.hexdigest()


def validate_intervals(
    conn,
    uretim_id,
    hammadde_id,
    parti_sayisi,
    intervals,
    recipe_kg,
):
    if not intervals:
        raise ValueError(
            "PARTI ARALIGI BOS OLAMAZ"
        )

    normalized = []

    for item in intervals:
        depo_kabul_id = int(
            item["depo_kabul_id"]
        )

        start = item["parti_baslangic"]
        end = item["parti_bitis"]

        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
        ):
            raise ValueError(
                "PARTI NUMARASI TAM SAYI OLMALI"
            )

        if start <= 0 or end <= 0:
            raise ValueError(
                "PARTI NUMARASI POZITIF OLMALI"
            )

        if start > end:
            raise ValueError(
                "PARTI BASLANGIC BITISTEN BUYUK"
            )

        if end > parti_sayisi:
            raise ValueError(
                "PARTI BITIS URETIMI ASIYOR"
            )

        lot = conn.execute("""
            SELECT
                hammadde_id,
                kabul_durumu
            FROM depo_kabul
            WHERE id = ?
        """, (depo_kabul_id,)).fetchone()

        if lot is None:
            raise ValueError(
                "DEPO KABUL LOTU BULUNAMADI"
            )

        if int(lot[0]) != int(hammadde_id):
            raise ValueError(
                "YANLIS HAMMADDE LOTU"
            )

        if str(lot[1]).upper() != "KABUL":
            raise ValueError(
                "LOT KABUL DURUMUNDA DEGIL"
            )

        batch_count = (
            end - start + 1
        )

        expected_kg = (
            batch_count * recipe_kg
        )

        manual_kg = item.get(
            "kullanilan_miktar_kg"
        )

        if (
            manual_kg is not None
            and abs(
                float(manual_kg)
                - float(expected_kg)
            ) > 0.000001
        ):
            raise ValueError(
                "MANUEL KG RECETEYLE CELISIYOR"
            )

        normalized.append({
            "uretim_id": uretim_id,
            "hammadde_id": hammadde_id,
            "depo_kabul_id": depo_kabul_id,
            "parti_baslangic": start,
            "parti_bitis": end,
            "kullanilan_miktar_kg": expected_kg,
        })

    normalized.sort(
        key=lambda x: (
            x["parti_baslangic"],
            x["parti_bitis"],
            x["depo_kabul_id"],
        )
    )

    expected_start = 1

    for item in normalized:
        start = item["parti_baslangic"]
        end = item["parti_bitis"]

        if start < expected_start:
            raise ValueError(
                "PARTI ARALIGI CAKISIYOR"
            )

        if start > expected_start:
            raise ValueError(
                "PARTI ARALIGINDA BOSLUK VAR"
            )

        expected_start = end + 1

    if expected_start != parti_sayisi + 1:
        raise ValueError(
            "PARTI ARALIGI URETIM SONUNA ULASMIYOR"
        )

    expected_total = (
        parti_sayisi * recipe_kg
    )

    actual_total = sum(
        item["kullanilan_miktar_kg"]
        for item in normalized
    )

    if abs(
        float(actual_total)
        - float(expected_total)
    ) > 0.000001:
        raise ValueError(
            "HAMMADDE KUTLE DENKLIGI HATASI"
        )

    return normalized


def expect_rejection(label, fn):
    try:
        fn()
    except ValueError:
        print(
            label,
            ": PASSED",
        )
        return

    raise RuntimeError(
        f"{label}: REJECTION FAILED"
    )


print("")
print(
    "=== REDBOX OS PHASE 16 "
    "MODEL B SANDBOX PROOF ==="
)

for path in PROTECTED:
    if not path.exists():
        raise RuntimeError(
            f"PROTECTED FILE MISSING: {path}"
        )

before_hashes = {
    str(path.relative_to(ROOT)): sha256(path)
    for path in PROTECTED
}


print("")
print("=== 1 / LIVE READ-ONLY PREFLIGHT ===")

live = sqlite3.connect(
    f"file:{LIVE_DB.resolve()}?mode=ro",
    uri=True,
)

try:
    integrity = live.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    fk = live.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    historical_count = live.execute("""
        SELECT COUNT(*)
        FROM uretim_hammadde_lotlari
    """).fetchone()[0]

    historical_before = historical_digest(
        live
    )

    print("INTEGRITY:", integrity)
    print(
        "FOREIGN KEY:",
        fk if fk else "OK",
    )
    print(
        "HISTORICAL TRACE ROWS:",
        historical_count,
    )

    if integrity != "ok":
        raise RuntimeError(
            "LIVE DB INTEGRITY FAILED"
        )

    if fk:
        raise RuntimeError(
            "LIVE DB FOREIGN KEY FAILED"
        )

    if historical_count != 88:
        raise RuntimeError(
            "HISTORICAL TRACE CONTRACT FAILED"
        )

finally:
    live.close()


with tempfile.TemporaryDirectory() as tmp:
    sandbox_db = (
        Path(tmp)
        / "phase16_sandbox.db"
    )

    shutil.copy2(
        LIVE_DB,
        sandbox_db,
    )

    if sandbox_db.resolve() == LIVE_DB.resolve():
        raise RuntimeError(
            "SANDBOX LIVE DB OLAMAZ"
        )

    print("")
    print("=== 2 / SANDBOX TARGET ===")
    print(
        "SANDBOX DB:",
        sandbox_db.resolve(),
    )

    conn = sqlite3.connect(
        sandbox_db
    )

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    try:
        print("")
        print(
            "=== 3 / MODEL B SCHEMA CREATE ==="
        )

        conn.execute("""
            CREATE TABLE
            uretim_hammadde_lot_parti_araliklari
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                uretim_id INTEGER NOT NULL,

                hammadde_id INTEGER NOT NULL,

                depo_kabul_id INTEGER NOT NULL,

                parti_baslangic INTEGER NOT NULL,

                parti_bitis INTEGER NOT NULL,

                kullanilan_miktar_kg
                    REAL NOT NULL,

                kayit_tipi TEXT NOT NULL
                    DEFAULT 'KESIN_PARTI_ARALIGI',

                kayit_zamani TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (uretim_id)
                    REFERENCES uretim(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (hammadde_id)
                    REFERENCES hammaddeler(id),

                FOREIGN KEY (depo_kabul_id)
                    REFERENCES depo_kabul(id),

                CHECK (
                    parti_baslangic > 0
                ),

                CHECK (
                    parti_bitis >= parti_baslangic
                ),

                CHECK (
                    kullanilan_miktar_kg >= 0
                )
            )
        """)

        conn.execute("""
            CREATE INDEX
            idx_uhlpa_uretim_hammadde
            ON
            uretim_hammadde_lot_parti_araliklari
            (
                uretim_id,
                hammadde_id,
                parti_baslangic
            )
        """)

        conn.execute("""
            CREATE INDEX
            idx_uhlpa_depo_kabul
            ON
            uretim_hammadde_lot_parti_araliklari
            (
                depo_kabul_id
            )
        """)

        conn.commit()

        print(
            "MODEL B SCHEMA: CREATED"
        )


        print("")
        print(
            "=== 4 / HISTORICAL PRESERVATION ==="
        )

        count_after_schema = conn.execute("""
            SELECT COUNT(*)
            FROM uretim_hammadde_lotlari
        """).fetchone()[0]

        digest_after_schema = historical_digest(
            conn
        )

        if count_after_schema != historical_count:
            raise RuntimeError(
                "HISTORICAL ROW COUNT CHANGED"
            )

        if digest_after_schema != historical_before:
            raise RuntimeError(
                "HISTORICAL CONTENT CHANGED"
            )

        print(
            "HISTORICAL TRACE ROW COUNT: PRESERVED"
        )

        print(
            "HISTORICAL TRACE CONTENT DIGEST: MATCH"
        )


        print("")
        print(
            "=== 5 / ACTIVE RECIPE CONTRACT ==="
        )

        recipe = conn.execute("""
            SELECT
                id,
                parti_teorik_kg
            FROM receteler
            WHERE aktif = 1
            ORDER BY id
            LIMIT 1
        """).fetchone()

        if recipe is None:
            raise RuntimeError(
                "ACTIVE RECIPE NOT FOUND"
            )

        recipe_id = recipe[0]

        materials = conn.execute("""
            SELECT
                rk.hammadde_id,
                h.ad,
                rk.miktar_kg
            FROM recete_kalemleri rk
            JOIN hammaddeler h
              ON h.id = rk.hammadde_id
            WHERE rk.recete_id = ?
            ORDER BY rk.hammadde_id
        """, (recipe_id,)).fetchall()

        if len(materials) != 8:
            raise RuntimeError(
                "ACTIVE RECIPE MATERIAL COUNT != 8"
            )

        raw_recipe_total = sum(
            float(row[2])
            for row in materials
        )

        print(
            "RECIPE ID:",
            recipe_id,
        )

        print(
            "RAW MATERIAL COUNT:",
            len(materials),
        )

        print(
            "RAW MATERIAL KG / BATCH:",
            f"{raw_recipe_total:.6f}",
        )


        print("")
        print(
            "=== 6 / SYNTHETIC 13-BATCH PRODUCTION ==="
        )

        conn.execute("""
            INSERT INTO uretim
            (
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
            VALUES
            (
                '31.12.2099',
                'PH16-SYNTH-PROD',
                13,
                265.356,
                0,
                265.356,
                'Fatih Ayaz',
                'Eda Ayaz',
                'PHASE16 SANDBOX',
                '31.12.2099 23:59:59'
            )
        """)

        synthetic_production_id = (
            conn.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]
        )

        conn.execute("""
            INSERT INTO uretim_recete
            (
                uretim_id,
                recete_id
            )
            VALUES (?, ?)
        """, (
            synthetic_production_id,
            recipe_id,
        ))

        lot_map = {}

        for index, material in enumerate(
            materials,
            start=1,
        ):
            hammadde_id = material[0]

            ids = []

            for suffix in ["A", "B"]:
                lot_no = (
                    f"PH16-SYNTH-{index}-{suffix}"
                )

                conn.execute("""
                    INSERT INTO depo_kabul
                    (
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
                    SELECT
                        '30.12.2099',
                        ?,
                        tedarikci,
                        ?,
                        '29.12.2099',
                        '29.12.2101',
                        9999,
                        'KABUL',
                        'PHASE16 SANDBOX',
                        '30.12.2099 12:00:00',
                        tedarikci_id
                    FROM depo_kabul
                    WHERE hammadde_id = ?
                    ORDER BY id
                    LIMIT 1
                """, (
                    hammadde_id,
                    lot_no,
                    hammadde_id,
                ))

                ids.append(
                    conn.execute(
                        "SELECT last_insert_rowid()"
                    ).fetchone()[0]
                )

            lot_map[hammadde_id] = ids

        first_material = materials[0]

        all_normalized = []

        for index, material in enumerate(materials):
            hammadde_id = material[0]
            recipe_kg = float(material[2])

            lot_a, lot_b = lot_map[
                hammadde_id
            ]

            if index == 0:
                intervals = [
                    {
                        "depo_kabul_id": lot_a,
                        "parti_baslangic": 1,
                        "parti_bitis": 6,
                    },
                    {
                        "depo_kabul_id": lot_b,
                        "parti_baslangic": 7,
                        "parti_bitis": 13,
                    },
                ]
            else:
                intervals = [
                    {
                        "depo_kabul_id": lot_a,
                        "parti_baslangic": 1,
                        "parti_bitis": 13,
                    },
                ]

            normalized = validate_intervals(
                conn,
                synthetic_production_id,
                hammadde_id,
                13,
                intervals,
                recipe_kg,
            )

            all_normalized.extend(
                normalized
            )

            for item in normalized:
                conn.execute("""
                    INSERT INTO
                    uretim_hammadde_lot_parti_araliklari
                    (
                        uretim_id,
                        hammadde_id,
                        depo_kabul_id,
                        parti_baslangic,
                        parti_bitis,
                        kullanilan_miktar_kg,
                        kayit_tipi
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    item["uretim_id"],
                    item["hammadde_id"],
                    item["depo_kabul_id"],
                    item["parti_baslangic"],
                    item["parti_bitis"],
                    item["kullanilan_miktar_kg"],
                    "KESIN_PARTI_ARALIGI",
                ))

        conn.commit()

        total_interval_kg = sum(
            float(item["kullanilan_miktar_kg"])
            for item in all_normalized
        )

        expected_recipe_kg = (
            13 * raw_recipe_total
        )

        if abs(
            total_interval_kg
            - expected_recipe_kg
        ) > 0.000001:
            raise RuntimeError(
                "TOTAL RECIPE MASS PROOF FAILED"
            )

        print(
            "13-BATCH SPLIT LOT PROOF: PASSED"
        )

        print(
            "8-MATERIAL COVERAGE: PASSED"
        )

        print(
            "RECIPE MASS DERIVATION: PASSED"
        )

        print(
            "EXPECTED RAW KG:",
            f"{expected_recipe_kg:.6f}",
        )

        print(
            "INTERVAL RAW KG:",
            f"{total_interval_kg:.6f}",
        )


        print("")
        print(
            "=== 7 / VALIDATION REJECTION MATRIX ==="
        )

        hm_id = first_material[0]
        recipe_kg = float(first_material[2])

        lot_a, lot_b = lot_map[hm_id]

        def validate(items):
            return validate_intervals(
                conn,
                synthetic_production_id,
                hm_id,
                13,
                items,
                recipe_kg,
            )

        expect_rejection(
            "INTERVAL GAP REJECTION",
            lambda: validate([
                {
                    "depo_kabul_id": lot_a,
                    "parti_baslangic": 1,
                    "parti_bitis": 6,
                },
                {
                    "depo_kabul_id": lot_b,
                    "parti_baslangic": 8,
                    "parti_bitis": 13,
                },
            ]),
        )

        expect_rejection(
            "INTERVAL OVERLAP REJECTION",
            lambda: validate([
                {
                    "depo_kabul_id": lot_a,
                    "parti_baslangic": 1,
                    "parti_bitis": 8,
                },
                {
                    "depo_kabul_id": lot_b,
                    "parti_baslangic": 7,
                    "parti_bitis": 13,
                },
            ]),
        )

        boundary_cases = [
            [
                {
                    "depo_kabul_id": lot_a,
                    "parti_baslangic": 2,
                    "parti_bitis": 13,
                }
            ],
            [
                {
                    "depo_kabul_id": lot_a,
                    "parti_baslangic": 1,
                    "parti_bitis": 12,
                }
            ],
            [
                {
                    "depo_kabul_id": lot_a,
                    "parti_baslangic": 0,
                    "parti_bitis": 13,
                }
            ],
            [
                {
                    "depo_kabul_id": lot_a,
                    "parti_baslangic": -1,
                    "parti_bitis": 13,
                }
            ],
            [
                {
                    "depo_kabul_id": lot_a,
                    "parti_baslangic": 8,
                    "parti_bitis": 7,
                }
            ],
            [
                {
                    "depo_kabul_id": lot_a,
                    "parti_baslangic": 1,
                    "parti_bitis": 14,
                }
            ],
        ]

        for case in boundary_cases:
            expect_rejection(
                "INTERVAL BOUNDARY CASE",
                lambda case=case: validate(case),
            )

        print(
            "INTERVAL BOUNDARY REJECTION: PASSED"
        )

        wrong_material = materials[1][0]
        wrong_lot = lot_map[
            wrong_material
        ][0]

        expect_rejection(
            "WRONG MATERIAL LOT REJECTION",
            lambda: validate([
                {
                    "depo_kabul_id": wrong_lot,
                    "parti_baslangic": 1,
                    "parti_bitis": 13,
                }
            ]),
        )

        conn.execute("""
            UPDATE depo_kabul
            SET kabul_durumu = 'RED'
            WHERE id = ?
        """, (lot_b,))

        expect_rejection(
            "REJECTED LOT STATUS REJECTION",
            lambda: validate([
                {
                    "depo_kabul_id": lot_b,
                    "parti_baslangic": 1,
                    "parti_bitis": 13,
                }
            ]),
        )

        conn.execute("""
            UPDATE depo_kabul
            SET kabul_durumu = 'KABUL'
            WHERE id = ?
        """, (lot_b,))

        expect_rejection(
            "MANUAL KG CONTRADICTION REJECTION",
            lambda: validate([
                {
                    "depo_kabul_id": lot_a,
                    "parti_baslangic": 1,
                    "parti_bitis": 13,
                    "kullanilan_miktar_kg": 999,
                }
            ]),
        )


        print("")
        print(
            "=== 8 / NON-ADJACENT SAME LOT PROOF ==="
        )

        non_adjacent = validate([
            {
                "depo_kabul_id": lot_a,
                "parti_baslangic": 1,
                "parti_bitis": 3,
            },
            {
                "depo_kabul_id": lot_b,
                "parti_baslangic": 4,
                "parti_bitis": 6,
            },
            {
                "depo_kabul_id": lot_a,
                "parti_baslangic": 7,
                "parti_bitis": 9,
            },
            {
                "depo_kabul_id": lot_b,
                "parti_baslangic": 10,
                "parti_bitis": 13,
            },
        ])

        if len(non_adjacent) != 4:
            raise RuntimeError(
                "NON-ADJACENT CAPABILITY FAILED"
            )

        print(
            "NON-ADJACENT SAME LOT CAPABILITY: PASSED"
        )


        print("")
        print(
            "=== 9 / FORWARD TRACEABILITY ==="
        )

        forward_rows = conn.execute("""
            SELECT
                u.urun_lot_no,
                h.ad,
                dk.tedarikci_lot_no,
                a.parti_baslangic,
                a.parti_bitis,
                (
                    a.parti_bitis
                    - a.parti_baslangic
                    + 1
                ) AS parti_adedi,
                a.kullanilan_miktar_kg
            FROM
                uretim_hammadde_lot_parti_araliklari a
            JOIN uretim u
              ON u.id = a.uretim_id
            JOIN hammaddeler h
              ON h.id = a.hammadde_id
            JOIN depo_kabul dk
              ON dk.id = a.depo_kabul_id
            WHERE a.uretim_id = ?
            ORDER BY
                h.id,
                a.parti_baslangic,
                a.id
        """, (
            synthetic_production_id,
        )).fetchall()

        if not forward_rows:
            raise RuntimeError(
                "FORWARD TRACE FAILED"
            )

        for row in forward_rows:
            print(tuple(row))

        print(
            "FORWARD TRACEABILITY QUERY: PASSED"
        )


        print("")
        print(
            "=== 10 / REVERSE RECALL ==="
        )

        reverse_rows = conn.execute("""
            SELECT
                u.id,
                u.urun_lot_no,
                h.ad,
                a.parti_baslangic,
                a.parti_bitis,
                a.kullanilan_miktar_kg
            FROM
                uretim_hammadde_lot_parti_araliklari a
            JOIN uretim u
              ON u.id = a.uretim_id
            JOIN hammaddeler h
              ON h.id = a.hammadde_id
            WHERE a.depo_kabul_id = ?
            ORDER BY
                u.id,
                a.parti_baslangic,
                a.id
        """, (lot_a,)).fetchall()

        if not reverse_rows:
            raise RuntimeError(
                "REVERSE RECALL FAILED"
            )

        for row in reverse_rows:
            print(tuple(row))

        print(
            "REVERSE RECALL QUERY: PASSED"
        )


        print("")
        print(
            "=== 11 / HISTORICAL DISPLAY ==="
        )

        historical_display = conn.execute("""
            SELECT
                COUNT(*)
            FROM uretim_hammadde_lotlari uhl
            WHERE NOT EXISTS
            (
                SELECT 1
                FROM
                uretim_hammadde_lot_parti_araliklari a
                WHERE
                    a.uretim_id = uhl.uretim_id
                    AND
                    a.depo_kabul_id = uhl.depo_kabul_id
            )
        """).fetchone()[0]

        if historical_display != 88:
            raise RuntimeError(
                "HISTORICAL DISPLAY CLASSIFICATION FAILED"
            )

        print(
            "HISTORICAL DISPLAY CLASSIFICATION:",
            "Tarihsel kayıt — parti aralığı belirtilmemiş",
        )

        print(
            "HISTORICAL DISPLAY CLASSIFICATION: PASSED"
        )


        print("")
        print(
            "=== 12 / SANDBOX FINAL VALIDATION ==="
        )

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        fk = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        print(
            "SANDBOX INTEGRITY:",
            integrity,
        )

        print(
            "SANDBOX FOREIGN KEYS:",
            fk if fk else "OK",
        )

        if integrity != "ok":
            raise RuntimeError(
                "SANDBOX INTEGRITY FAILED"
            )

        if fk:
            raise RuntimeError(
                "SANDBOX FOREIGN KEY FAILED"
            )

    finally:
        conn.close()


print("")
print(
    "=== 13 / PROTECTED HASH POSTCHECK ==="
)

for path in PROTECTED:
    rel = str(
        path.relative_to(ROOT)
    )

    current = sha256(path)

    if current != before_hashes[rel]:
        raise RuntimeError(
            f"PROTECTED HASH CHANGED: {rel}"
        )

    print(
        rel,
        ": MATCH",
    )


print("")
print(
    "PHASE 16 MODEL A: INSUFFICIENT"
)

print(
    "PHASE 16 MODEL B: SUFFICIENT"
)

print(
    "SELECTED MODEL: "
    "URETIM_HAMMADDE_LOT_PARTI_ARALIKLARI"
)

print("")
print(
    "HISTORICAL TRACE ROW COUNT: PRESERVED"
)

print(
    "HISTORICAL TRACE CONTENT DIGEST: MATCH"
)

print(
    "13-BATCH SPLIT LOT PROOF: PASSED"
)

print(
    "8-MATERIAL COVERAGE: PASSED"
)

print(
    "INTERVAL GAP REJECTION: PASSED"
)

print(
    "INTERVAL OVERLAP REJECTION: PASSED"
)

print(
    "INTERVAL BOUNDARY REJECTION: PASSED"
)

print(
    "WRONG MATERIAL LOT REJECTION: PASSED"
)

print(
    "REJECTED LOT STATUS REJECTION: PASSED"
)

print(
    "RECIPE MASS DERIVATION: PASSED"
)

print(
    "MANUAL KG CONTRADICTION REJECTION: PASSED"
)

print(
    "NON-ADJACENT SAME LOT CAPABILITY: PASSED"
)

print(
    "FORWARD TRACEABILITY QUERY: PASSED"
)

print(
    "REVERSE RECALL QUERY: PASSED"
)

print(
    "HISTORICAL DISPLAY CLASSIFICATION: PASSED"
)

print(
    "SANDBOX INTEGRITY: PASSED"
)

print(
    "SANDBOX FOREIGN KEYS: PASSED"
)

print("")
print(
    "PHASE 16 MODEL B SANDBOX PROOF PASSED"
)

print("")
print(
    "NOT: LIVE DB DEGISTIRILMEDI"
)

print(
    "NOT: APP.PY DEGISTIRILMEDI"
)

print(
    "NOT: ENGINE DEGISTIRILMEDI"
)

print("")
print(
    "NEXT: PHASE 17 CONTROLLED LIVE IMPLEMENTATION"
)

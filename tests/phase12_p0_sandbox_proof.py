import hashlib
import importlib.util
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DB = (PROJECT_ROOT / "database" / "redbox_os.db").resolve()
BASELINE_DIR = (
    PROJECT_ROOT / "backups" / "PHASE9_FINAL_20260709_144106"
).resolve()
BASELINE_DB = (BASELINE_DIR / "redbox_os.db").resolve()
PROTECTED_FILES = [
    LIVE_DB,
    BASELINE_DB,
    PROJECT_ROOT / "app.py",
    PROJECT_ROOT / "database" / "db.py",
    PROJECT_ROOT / "database" / "stock_engine.py",
    PROJECT_ROOT / "database" / "raw_material_stock_engine.py",
    PROJECT_ROOT / "database" / "finished_stock_engine.py",
    PROJECT_ROOT / "database" / "report_engine.py",
    PROJECT_ROOT / "tests" / "test_phase9_baseline.py",
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quote_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def stable_value(value):
    if isinstance(value, bytes):
        return {"blob_hex": value.hex()}
    return value


def stable_digest(payload):
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def connect_rw(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def connect_ro(db_path):
    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def user_tables(conn):
    return [
        row["name"]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    ]


def logical_fingerprint(db_path):
    conn = connect_ro(db_path)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        fk_rows = [dict(row) for row in conn.execute("PRAGMA foreign_key_check")]
        schema_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT type, name, tbl_name, sql
                FROM sqlite_master
                WHERE name NOT LIKE 'sqlite_%'
                ORDER BY type, name, tbl_name
                """
            ).fetchall()
        ]
        tables = user_tables(conn)
        row_counts = {}
        content_digests = {}

        for table in tables:
            table_sql = quote_identifier(table)
            info = [
                dict(row)
                for row in conn.execute(
                    f"PRAGMA table_info({table_sql})"
                ).fetchall()
            ]
            columns = [row["name"] for row in info]
            pk_columns = [
                row["name"]
                for row in sorted(info, key=lambda item: item["pk"])
                if row["pk"]
            ]
            order_columns = pk_columns or columns
            order_sql = ", ".join(quote_identifier(col) for col in order_columns)
            column_sql = ", ".join(quote_identifier(col) for col in columns)
            rows = [
                [stable_value(row[col]) for col in columns]
                for row in conn.execute(
                    f"SELECT {column_sql} FROM {table_sql} ORDER BY {order_sql}"
                ).fetchall()
            ]
            row_counts[table] = len(rows)
            content_digests[table] = stable_digest(
                {
                    "columns": columns,
                    "rows": rows,
                }
            )

        return {
            "integrity": integrity,
            "foreign_key_rows": fk_rows,
            "tables": tables,
            "schema_digest": stable_digest(schema_rows),
            "row_counts": row_counts,
            "content_digests": content_digests,
        }
    finally:
        conn.close()


def compare_fingerprints(before, after):
    return {
        "integrity_match": before["integrity"] == after["integrity"],
        "foreign_key_match": before["foreign_key_rows"] == after["foreign_key_rows"],
        "tables_match": before["tables"] == after["tables"],
        "schema_digest_match": before["schema_digest"] == after["schema_digest"],
        "row_count_differences": {
            table: {
                "before": before["row_counts"].get(table),
                "after": after["row_counts"].get(table),
            }
            for table in sorted(
                set(before["row_counts"]) | set(after["row_counts"])
            )
            if before["row_counts"].get(table) != after["row_counts"].get(table)
        },
        "content_digest_differences": {
            table: {
                "before": before["content_digests"].get(table),
                "after": after["content_digests"].get(table),
            }
            for table in sorted(
                set(before["content_digests"]) | set(after["content_digests"])
            )
            if before["content_digests"].get(table)
            != after["content_digests"].get(table)
        },
    }


def print_comparison(label, comparison):
    print(label)
    print(json.dumps(comparison, indent=2, ensure_ascii=False, sort_keys=True))


def assert_sandbox_target(sandbox_db):
    sandbox_db = sandbox_db.resolve()
    print(f"TARGET DB: {sandbox_db}")
    assert sandbox_db != LIVE_DB
    assert sandbox_db != BASELINE_DB
    assert BASELINE_DIR not in sandbox_db.parents


def sandbox_copy(temp_dir, name):
    target = Path(temp_dir) / name
    shutil.copy2(BASELINE_DB, target)
    return target.resolve()


def proof_a_init_database():
    print("\n=== PROOF A: init_database behavior ===")
    with tempfile.TemporaryDirectory() as temp_dir:
        sandbox_db = sandbox_copy(temp_dir, "redbox_os_phase12_init.db")
        print(f"SANDBOX DB: {sandbox_db}")
        assert_sandbox_target(sandbox_db)
        before = logical_fingerprint(sandbox_db)

        module_path = PROJECT_ROOT / "database" / "db.py"
        spec = importlib.util.spec_from_file_location(
            "phase12_isolated_database_db",
            module_path,
        )
        isolated_db_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(isolated_db_module)
        isolated_db_module.DB_PATH = sandbox_db

        assert isolated_db_module.DB_PATH.resolve() == sandbox_db.resolve()
        assert sandbox_db.resolve() != LIVE_DB
        assert BASELINE_DIR not in sandbox_db.resolve().parents

        isolated_db_module.init_database()
        after = logical_fingerprint(sandbox_db)
        comparison = compare_fingerprints(before, after)
        print_comparison("PROOF_A_COMPARISON", comparison)

        all_match = (
            comparison["integrity_match"]
            and comparison["foreign_key_match"]
            and comparison["tables_match"]
            and comparison["schema_digest_match"]
            and not comparison["row_count_differences"]
            and not comparison["content_digest_differences"]
        )
        result = (
            "P0-A DISPROVED FOR CURRENT PHASE 9 DATABASE STATE"
            if all_match
            else "P0-A PROVED"
        )
        print(f"PROOF_A_RESULT: {result}")
        return {
            "before": before,
            "after": after,
            "comparison": comparison,
            "result": result,
        }


def source_delete_statements():
    app_text = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    return {
        "depo_kabul_sil": "DELETE FROM depo_kabul WHERE id = ?"
        if "DELETE FROM depo_kabul WHERE id = ?" in app_text
        else "NOT FOUND",
        "uretim_sil": "DELETE FROM uretim WHERE id = ?"
        if "DELETE FROM uretim WHERE id = ?" in app_text
        else "NOT FOUND",
    }


def referenced_depo_rows(conn):
    return conn.execute(
        """
        SELECT
            dk.id,
            dk.hammadde_id,
            h.ad AS hammadde,
            dk.tedarikci_lot_no,
            COUNT(uhl.id) AS trace_count
        FROM depo_kabul dk
        JOIN hammaddeler h
          ON h.id = dk.hammadde_id
        JOIN uretim_hammadde_lotlari uhl
          ON uhl.depo_kabul_id = dk.id
        GROUP BY dk.id, dk.hammadde_id, h.ad, dk.tedarikci_lot_no
        ORDER BY dk.id
        """
    ).fetchall()


def unreferenced_depo_rows(conn):
    return conn.execute(
        """
        SELECT
            dk.id,
            dk.hammadde_id,
            h.ad AS hammadde,
            dk.tedarikci_lot_no
        FROM depo_kabul dk
        JOIN hammaddeler h
          ON h.id = dk.hammadde_id
        LEFT JOIN uretim_hammadde_lotlari uhl
          ON uhl.depo_kabul_id = dk.id
        WHERE uhl.id IS NULL
        ORDER BY dk.id
        """
    ).fetchall()


def count_referencing_tables(conn, parent_table):
    refs = {}
    for table in user_tables(conn):
        table_sql = quote_identifier(table)
        for fk in conn.execute(f"PRAGMA foreign_key_list({table_sql})"):
            if fk["table"] == parent_table:
                refs.setdefault(table, []).append(dict(fk))
    return refs


def proof_b_depo_delete():
    print("\n=== PROOF B: depo_kabul delete behavior ===")
    with tempfile.TemporaryDirectory() as temp_dir:
        sandbox_db = sandbox_copy(temp_dir, "redbox_os_phase12_depo_delete.db")
        print(f"SANDBOX DB: {sandbox_db}")
        assert_sandbox_target(sandbox_db)
        conn = connect_rw(sandbox_db)
        try:
            refs = referenced_depo_rows(conn)
            unrefs = unreferenced_depo_rows(conn)
            other_fk = count_referencing_tables(conn, "depo_kabul")
            print(
                "DEPO_CATEGORY_COUNTS: "
                + json.dumps(
                    {
                        "referenced_by_uretim_hammadde_lotlari": len(refs),
                        "not_referenced_by_uretim_hammadde_lotlari": len(unrefs),
                        "referencing_fk_tables": sorted(other_fk),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            results = {
                "category_counts": {
                    "referenced": len(refs),
                    "unreferenced": len(unrefs),
                    "referencing_fk_tables": sorted(other_fk),
                },
                "referenced_result": None,
                "unreferenced_result": None,
            }

            if refs:
                target = refs[0]
                assert_sandbox_target(sandbox_db)
                conn.execute("BEGIN")
                try:
                    conn.execute(
                        "DELETE FROM depo_kabul WHERE id = ?",
                        (target["id"],),
                    )
                    row_counts = {
                        "depo_kabul": conn.execute(
                            "SELECT COUNT(*) FROM depo_kabul"
                        ).fetchone()[0],
                        "trace_rows_for_target": conn.execute(
                            """
                            SELECT COUNT(*)
                            FROM uretim_hammadde_lotlari
                            WHERE depo_kabul_id = ?
                            """,
                            (target["id"],),
                        ).fetchone()[0],
                    }
                    results["referenced_result"] = {
                        "status": "REFERENCED DEPO_KABUL DELETE ALLOWED",
                        "target": dict(target),
                        "inside_transaction_counts": row_counts,
                    }
                except sqlite3.IntegrityError as exc:
                    results["referenced_result"] = {
                        "status": "REFERENCED DEPO_KABUL DELETE BLOCKED BY FK",
                        "target": dict(target),
                        "error": str(exc),
                    }
                finally:
                    conn.rollback()

            if unrefs:
                target = unrefs[0]
                before_count = conn.execute(
                    "SELECT COUNT(*) FROM depo_kabul"
                ).fetchone()[0]
                assert_sandbox_target(sandbox_db)
                conn.execute("BEGIN")
                try:
                    cursor = conn.execute(
                        "DELETE FROM depo_kabul WHERE id = ?",
                        (target["id"],),
                    )
                    after_count = conn.execute(
                        "SELECT COUNT(*) FROM depo_kabul"
                    ).fetchone()[0]
                    results["unreferenced_result"] = {
                        "status": "UNREFERENCED DEPO_KABUL DELETE ALLOWED",
                        "target": dict(target),
                        "affected_rows": cursor.rowcount,
                        "before_count": before_count,
                        "inside_transaction_count": after_count,
                    }
                except sqlite3.IntegrityError as exc:
                    results["unreferenced_result"] = {
                        "status": "UNREFERENCED DEPO_KABUL DELETE BLOCKED BY FK",
                        "target": dict(target),
                        "error": str(exc),
                    }
                finally:
                    conn.rollback()
            else:
                results["unreferenced_result"] = {
                    "status": "NO UNREFERENCED DEPO_KABUL ROW AVAILABLE"
                }

            print("PROOF_B_RESULT")
            print(json.dumps(results, indent=2, ensure_ascii=False, sort_keys=True))
            return results
        finally:
            conn.close()


def production_dependency_matrix(conn):
    rows = conn.execute(
        """
        SELECT
            u.id,
            u.urun_lot_no,
            COUNT(DISTINCT ur.id) AS uretim_recete_count,
            COUNT(DISTINCT uhl.id) AS trace_count,
            COUNT(DISTINCT p.id) AS packaging_count,
            COUNT(DISTINCT sk.id) AS shipment_line_count
        FROM uretim u
        LEFT JOIN uretim_recete ur
          ON ur.uretim_id = u.id
        LEFT JOIN uretim_hammadde_lotlari uhl
          ON uhl.uretim_id = u.id
        LEFT JOIN paketleme p
          ON p.uretim_id = u.id
        LEFT JOIN sevkiyat_kalemleri sk
          ON sk.paketleme_id = p.id
        GROUP BY u.id, u.urun_lot_no
        ORDER BY u.id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def phase9_counts_and_totals(conn):
    return {
        "uretim": conn.execute("SELECT COUNT(*) FROM uretim").fetchone()[0],
        "uretim_recete": conn.execute(
            "SELECT COUNT(*) FROM uretim_recete"
        ).fetchone()[0],
        "uretim_hammadde_lotlari": conn.execute(
            "SELECT COUNT(*) FROM uretim_hammadde_lotlari"
        ).fetchone()[0],
        "paketleme": conn.execute("SELECT COUNT(*) FROM paketleme").fetchone()[0],
        "sevkiyat": conn.execute("SELECT COUNT(*) FROM sevkiyat").fetchone()[0],
        "sevkiyat_kalemleri": conn.execute(
            "SELECT COUNT(*) FROM sevkiyat_kalemleri"
        ).fetchone()[0],
        "net_production": conn.execute(
            "SELECT COALESCE(SUM(net_uretim_kg), 0) FROM uretim"
        ).fetchone()[0],
        "packaged": conn.execute(
            "SELECT COALESCE(SUM(paketlenen_kg), 0) FROM paketleme"
        ).fetchone()[0],
        "packaging_waste": conn.execute(
            "SELECT COALESCE(SUM(paketleme_firesi_kg), 0) FROM paketleme"
        ).fetchone()[0],
        "shipped": conn.execute(
            "SELECT COALESCE(SUM(sevk_kg), 0) FROM sevkiyat_kalemleri"
        ).fetchone()[0],
    }


def attempt_production_delete(conn, sandbox_db, target):
    assert_sandbox_target(sandbox_db)
    before = dict(target)
    conn.execute("BEGIN")
    try:
        conn.execute("DELETE FROM uretim WHERE id = ?", (target["id"],))
        after = {
            "remaining_uretim": conn.execute(
                "SELECT COUNT(*) FROM uretim WHERE id = ?",
                (target["id"],),
            ).fetchone()[0],
            "remaining_uretim_recete": conn.execute(
                "SELECT COUNT(*) FROM uretim_recete WHERE uretim_id = ?",
                (target["id"],),
            ).fetchone()[0],
            "remaining_trace_rows": conn.execute(
                """
                SELECT COUNT(*)
                FROM uretim_hammadde_lotlari
                WHERE uretim_id = ?
                """,
                (target["id"],),
            ).fetchone()[0],
            "remaining_packaging": conn.execute(
                "SELECT COUNT(*) FROM paketleme WHERE uretim_id = ?",
                (target["id"],),
            ).fetchone()[0],
            "reachable_shipment_lines": conn.execute(
                """
                SELECT COUNT(*)
                FROM sevkiyat_kalemleri sk
                JOIN paketleme p
                  ON p.id = sk.paketleme_id
                WHERE p.uretim_id = ?
                """,
                (target["id"],),
            ).fetchone()[0],
            "global_counts_and_totals": phase9_counts_and_totals(conn),
            "foreign_key_check_rows": len(
                conn.execute("PRAGMA foreign_key_check").fetchall()
            ),
        }
        return {
            "status": "URETIM DELETE ALLOWED",
            "target_before": before,
            "inside_transaction": after,
        }
    except sqlite3.IntegrityError as exc:
        return {
            "status": "URETIM DELETE BLOCKED BY FK",
            "target_before": before,
            "error": str(exc),
        }
    finally:
        conn.rollback()


def proof_c_uretim_delete():
    print("\n=== PROOF C: uretim delete behavior ===")
    with tempfile.TemporaryDirectory() as temp_dir:
        sandbox_db = sandbox_copy(temp_dir, "redbox_os_phase12_uretim_delete.db")
        print(f"SANDBOX DB: {sandbox_db}")
        assert_sandbox_target(sandbox_db)
        conn = connect_rw(sandbox_db)
        try:
            matrix = production_dependency_matrix(conn)
            print("PRODUCTION_DEPENDENCY_MATRIX")
            print(json.dumps(matrix, indent=2, ensure_ascii=False, sort_keys=True))

            categories = {}
            for row in matrix:
                if row["packaging_count"] > 0 and row["shipment_line_count"] > 0:
                    categories.setdefault(
                        "A_packaging_and_shipment_dependencies",
                        row,
                    )
                if row["packaging_count"] > 0 and row["shipment_line_count"] == 0:
                    categories.setdefault(
                        "B_packaging_no_shipment_dependency",
                        row,
                    )
                if row["packaging_count"] == 0:
                    categories.setdefault("C_no_packaging", row)

            tested = {}
            for category, target in categories.items():
                tested[category] = attempt_production_delete(
                    conn,
                    sandbox_db,
                    target,
                )

            result = {
                "dependency_matrix": matrix,
                "tested_categories": tested,
                "available_categories": sorted(categories),
            }
            print("PROOF_C_RESULT")
            print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
            return result
        finally:
            conn.close()


def proof_d_query_only():
    print("\n=== PROOF D: query_only observation ===")
    with tempfile.TemporaryDirectory() as temp_dir:
        sandbox_db = sandbox_copy(temp_dir, "redbox_os_phase12_query_only.db")
        print(f"SANDBOX DB: {sandbox_db}")
        assert_sandbox_target(sandbox_db)
        conn = connect_rw(sandbox_db)
        try:
            default_value = conn.execute("PRAGMA query_only").fetchone()[0]
            conn.execute("PRAGMA query_only = ON")
            enabled_value = conn.execute("PRAGMA query_only").fetchone()[0]
        finally:
            conn.close()

    runtime_source = (PROJECT_ROOT / "database" / "db.py").read_text(encoding="utf-8")
    app_source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    runtime_sets_query_only = (
        "PRAGMA query_only" in runtime_source or "PRAGMA query_only" in app_source
    )
    result = {
        "default_query_only": default_value,
        "after_enable_query_only": enabled_value,
        "runtime_connections_set_query_only": runtime_sets_query_only,
    }
    print("PROOF_D_RESULT")
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return result


def main():
    print("REDBOX OS PHASE 12 P0 SANDBOX BEHAVIOR PROOF")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"LIVE_DB: {LIVE_DB}")
    print(f"BASELINE_DB: {BASELINE_DB}")
    pre_hashes = {str(path): sha256(path) for path in PROTECTED_FILES}

    delete_sql = source_delete_statements()
    print("SOURCE_DELETE_STATEMENTS")
    print(json.dumps(delete_sql, indent=2, ensure_ascii=False, sort_keys=True))

    results = {
        "proof_a": proof_a_init_database(),
        "proof_b": proof_b_depo_delete(),
        "proof_c": proof_c_uretim_delete(),
        "proof_d": proof_d_query_only(),
    }

    post_hashes = {str(path): sha256(path) for path in PROTECTED_FILES}
    hash_matches = {
        path: pre_hashes[path] == post_hashes[path]
        for path in sorted(pre_hashes)
    }
    print("\nPROTECTED_HASH_MATCHES")
    print(json.dumps(hash_matches, indent=2, ensure_ascii=False, sort_keys=True))
    if not all(hash_matches.values()):
        changed = [path for path, matches in hash_matches.items() if not matches]
        raise SystemExit(f"PROTECTED HASH CHANGED: {changed}")

    print("\nPHASE12_RESULTS_JSON")
    print(json.dumps(results, indent=2, ensure_ascii=False, sort_keys=True))
    print("PHASE12_SCRIPT_COMPLETED")


if __name__ == "__main__":
    main()

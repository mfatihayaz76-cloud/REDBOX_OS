import argparse
import hashlib
import json
import math
import re
import sqlite3
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ACCEPTANCE_CRITERIA = (
    "clean_install",
    "first_user",
    "catalog_60_plus",
    "full_business_cycle",
    "traceability_recall",
    "permissions",
    "audit",
    "backup_restore",
    "pdf",
    "performance",
)

PERFORMANCE_LIMITS = {
    "median_ms": 50.0,
    "p95_ms": 150.0,
    "max_ms": 300.0,
}


def acceptance_test_modules():
    return {
        "clean_install": (
            "tests.test_distribution_installation_acceptance",
            "tests.test_company_neutral_fresh_install",
        ),
        "first_user": (
            "tests.test_first_setup_engine",
            "tests.test_login_first_setup_integration",
        ),
        "catalog_60_plus": (
            "tests.test_recipe_import_preflight",
            "tests.test_recipe_import_atomic",
        ),
        "full_business_cycle": (
            "tests.test_business_rules_sandbox",
        ),
        "traceability_recall": (
            "tests.test_business_rules_sandbox",
            "tests.test_phase9_baseline",
        ),
        "permissions": (
            "tests.test_login_license_routing",
            "tests.test_recipe_approval_engine",
        ),
        "audit": (
            "tests.test_audit_engine_contract",
            "tests.test_first_setup_engine",
        ),
        "backup_restore": (
            "tests.test_backup_restore_engine",
            "tests.test_backup_recovery_engine",
        ),
        "pdf": (
            "tests.test_recipe_pdf_contract",
        ),
        "performance": (
            "tests.test_commercial_final_acceptance",
        ),
    }


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_only_connection(database_path):
    resolved = Path(database_path).resolve()
    return sqlite3.connect(
        f"file:{resolved.as_posix()}?mode=ro",
        uri=True,
    )


def database_performance_probe(database_path, iterations=25):
    database_path = Path(database_path)

    if iterations < 1:
        raise ValueError("iterations en az 1 olmalıdır.")

    before_sha = _sha256(database_path)
    durations = []

    queries = (
        "SELECT COUNT(*) FROM urunler",
        "SELECT COUNT(*) FROM receteler",
        "SELECT COUNT(*) FROM uretim",
        "SELECT COUNT(*) FROM paketleme",
        "SELECT COUNT(*) FROM sevkiyat",
        (
            "SELECT u.id, COUNT(r.id) "
            "FROM urunler AS u "
            "LEFT JOIN receteler AS r ON r.urun_id = u.id "
            "GROUP BY u.id ORDER BY u.id LIMIT 100"
        ),
    )

    connection = _read_only_connection(database_path)
    try:
        connection.execute("PRAGMA query_only = ON")

        for _ in range(iterations):
            started = time.perf_counter_ns()

            for query in queries:
                connection.execute(query).fetchall()

            elapsed_ms = (
                time.perf_counter_ns() - started
            ) / 1_000_000
            durations.append(elapsed_ms)

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
        foreign_key_violations = len(
            connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
        )
    finally:
        connection.close()

    after_sha = _sha256(database_path)
    ordered = sorted(durations)
    p95_index = max(
        0,
        math.ceil(len(ordered) * 0.95) - 1,
    )

    result = {
        "iterations": iterations,
        "median_ms": round(
            statistics.median(durations),
            6,
        ),
        "p95_ms": round(ordered[p95_index], 6),
        "max_ms": round(max(durations), 6),
        "integrity": integrity,
        "foreign_key_violations": (
            foreign_key_violations
        ),
        "database_preserved": before_sha == after_sha,
    }
    result["passed"] = (
        result["database_preserved"]
        and result["integrity"] == "ok"
        and result["foreign_key_violations"] == 0
        and result["median_ms"]
        <= PERFORMANCE_LIMITS["median_ms"]
        and result["p95_ms"]
        <= PERFORMANCE_LIMITS["p95_ms"]
        and result["max_ms"]
        <= PERFORMANCE_LIMITS["max_ms"]
    )
    return result


def validate_release_artifacts(dmg_path, manifest_path):
    dmg_path = Path(dmg_path)
    manifest_path = Path(manifest_path)

    if not dmg_path.is_file():
        raise FileNotFoundError(dmg_path)
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    actual_sha = _sha256(dmg_path)
    expected_sha = manifest["dmg"]["sha256"]

    verification = subprocess.run(
        (
            "/usr/bin/hdiutil",
            "verify",
            str(dmg_path),
        ),
        text=True,
        capture_output=True,
        check=False,
    )

    result = {
        "version": str(manifest["version"]),
        "build": str(manifest["build"]),
        "schema_version": int(
            manifest["fresh_database"][
                "schema_version"
            ]
        ),
        "dmg_sha256": actual_sha,
        "dmg_sha_matches": actual_sha == expected_sha,
        "dmg_verify_exit": verification.returncode,
    }
    result["passed"] = (
        result["version"] == "1.0.0"
        and result["build"] == "1"
        and result["schema_version"] == 13
        and result["dmg_sha_matches"]
        and result["dmg_verify_exit"] == 0
    )
    return result

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_DATABASE = PROJECT_ROOT / "database" / "redbox_os.db"
DEFAULT_DMG = (
    PROJECT_ROOT
    / "release"
    / "com4"
    / "REDBOX_OS-1.0.0-1.dmg"
)
DEFAULT_MANIFEST = (
    PROJECT_ROOT
    / "release"
    / "com4"
    / "REDBOX_OS-1.0.0-1-manifest.json"
)


def _unique_acceptance_modules():
    modules = []
    mapping = acceptance_test_modules()

    for criterion in ACCEPTANCE_CRITERIA:
        for module in mapping[criterion]:
            if module not in modules:
                modules.append(module)

    return modules


def run_commercial_acceptance(
    report_path=None,
    database_path=LIVE_DATABASE,
    dmg_path=DEFAULT_DMG,
    manifest_path=DEFAULT_MANIFEST,
):
    database_path = Path(database_path)
    before_sha = _sha256(database_path)
    modules = _unique_acceptance_modules()

    test_result = subprocess.run(
        (
            sys.executable,
            "-m",
            "unittest",
            "-v",
            *modules,
        ),
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    combined_output = (
        test_result.stdout + test_result.stderr
    )
    match = re.search(
        r"Ran\s+(\d+)\s+tests?",
        combined_output,
    )
    test_count = int(match.group(1)) if match else 0

    performance = database_performance_probe(
        database_path,
        iterations=100,
    )
    release = validate_release_artifacts(
        dmg_path,
        manifest_path,
    )
    after_sha = _sha256(database_path)

    criteria = {
        criterion: {
            "modules": list(
                acceptance_test_modules()[criterion]
            ),
            "passed": test_result.returncode == 0,
        }
        for criterion in ACCEPTANCE_CRITERIA
    }

    report = {
        "format": "REDBOX_COMMERCIAL_ACCEPTANCE_V1",
        "generated_at": (
            datetime.now().astimezone().isoformat()
        ),
        "product": "REDBOX OS",
        "version": release["version"],
        "build": release["build"],
        "criteria": criteria,
        "test_modules": modules,
        "test_count": test_count,
        "test_exit": test_result.returncode,
        "performance": performance,
        "release": release,
        "live_database": {
            "sha256_before": before_sha,
            "sha256_after": after_sha,
            "preserved": before_sha == after_sha,
        },
    }
    report["passed"] = (
        test_result.returncode == 0
        and test_count > 0
        and performance["passed"]
        and release["passed"]
        and report["live_database"]["preserved"]
        and all(
            item["passed"]
            for item in criteria.values()
        )
    )

    if report_path is not None:
        report_path = Path(report_path)
        report_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        report_path.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    return report, combined_output


def main():
    parser = argparse.ArgumentParser(
        description=(
            "REDBOX OS ticari final kabulünü "
            "salt-okunur kontrollerle çalıştırır."
        )
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Eşlenmiş ticari kabul testlerini çalıştır.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=(
            PROJECT_ROOT
            / "release"
            / "com5"
            / "REDBOX_OS-1.0.0-1-commercial-acceptance.json"
        ),
        help="JSON kabul raporu hedefi.",
    )
    arguments = parser.parse_args()

    if not arguments.run:
        parser.print_help()
        return 0

    report, output = run_commercial_acceptance(
        report_path=arguments.report,
    )
    print(output, end="")
    print(json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

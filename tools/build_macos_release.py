"""REDBOX OS için kontrollü macOS uygulama ve DMG üretimi."""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from application_metadata import (
    APP_BUILD,
    APP_DISPLAY_NAME,
    APP_VERSION,
    BUNDLE_IDENTIFIER,
)
from database.migrations import LATEST_SCHEMA_VERSION


BUILD_ROOT = PROJECT_ROOT / "build" / "macos"
DIST_ROOT = PROJECT_ROOT / "dist" / "macos"
RELEASE_ROOT = PROJECT_ROOT / "release" / "macos"

RELEASE_DOCUMENTS = (
    PROJECT_ROOT / "docs" / "KULLANICI_KILAVUZU.md",
    PROJECT_ROOT / "docs" / "KURULUM_KILAVUZU_MACOS.md",
    PROJECT_ROOT / "docs" / "LISANS_VE_DESTEK.md",
    PROJECT_ROOT / "docs" / "SURUM_NOTLARI_1.1.0.md",
    PROJECT_ROOT / "docs" / "USB_DEMO_TESLIM_KILAVUZU.md",
)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(block)
    return digest.hexdigest()


def release_document_paths():
    missing = [
        path
        for path in RELEASE_DOCUMENTS
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(
            f"Dağıtım belgeleri eksik: {missing}"
        )
    return RELEASE_DOCUMENTS


def release_artifact_names():
    release_id = f"{APP_VERSION}-{APP_BUILD}"
    return {
        "app": f"{APP_DISPLAY_NAME}.app",
        "dmg": f"REDBOX_OS-{release_id}.dmg",
        "manifest": (
            f"REDBOX_OS-{release_id}-manifest.json"
        ),
    }


def validate_distribution_database(database_path):
    database_path = Path(database_path)
    if not database_path.is_file():
        raise FileNotFoundError(
            f"Dağıtım veritabanı bulunamadı: "
            f"{database_path}"
        )

    before_sha = _sha256(database_path)
    connection = sqlite3.connect(
        f"{database_path.resolve().as_uri()}?mode=ro",
        uri=True,
    )
    try:
        schema_version = connection.execute(
            "PRAGMA user_version"
        ).fetchone()[0]
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
        tables = {
            row[0]
            for row in connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
            """).fetchall()
        }

        protected_tables = (
            "firma_profili",
            "kullanici_hesaplari",
            "personeller",
            "urunler",
            "receteler",
            "uretim",
            "paketleme",
            "sevkiyat",
            "lisans_kayitlari",
            "lisans_dogrulama_kayitlari",
        )
        counts = {
            table: connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            for table in protected_tables
            if table in tables
        }
    finally:
        connection.close()

    after_sha = _sha256(database_path)
    if before_sha != after_sha:
        raise RuntimeError(
            "Salt-okunur dağıtım DB kontrolü "
            "dosyayı değiştirdi."
        )
    if schema_version != LATEST_SCHEMA_VERSION:
        raise RuntimeError(
            "Dağıtım DB şeması güncel değil: "
            f"{schema_version}"
        )
    if integrity != "ok":
        raise RuntimeError(
            f"Dağıtım DB integrity hatası: {integrity}"
        )
    if foreign_keys:
        raise RuntimeError(
            "Dağıtım DB foreign-key ihlali: "
            f"{foreign_keys}"
        )
    if any(counts.values()):
        raise RuntimeError(
            "Dağıtım DB gerçek/operasyonel kayıt içeriyor: "
            f"{counts}"
        )

    return {
        "path": database_path,
        "sha256": before_sha,
        "schema_version": schema_version,
        "integrity": integrity,
        "foreign_key_violations": foreign_keys,
        "protected_counts": counts,
    }


def create_fresh_install_database(target_path):
    target_path = Path(target_path)
    if target_path.exists():
        raise FileExistsError(
            f"Dağıtım DB hedefi zaten var: {target_path}"
        )

    target_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    import database.db as database_module

    original_path = database_module.DB_PATH
    try:
        database_module.DB_PATH = target_path
        database_module.init_database()
    finally:
        database_module.DB_PATH = original_path

    return validate_distribution_database(
        target_path
    )


def _reset_scoped_directory(path, allowed_parent):
    path = Path(path).resolve()
    allowed_parent = Path(allowed_parent).resolve()

    if path.parent != allowed_parent:
        raise RuntimeError(
            f"Güvensiz çıktı temizleme hedefi: {path}"
        )

    if path.exists():
        shutil.rmtree(path)

    path.mkdir(parents=True, exist_ok=False)


def _run(command, *, environment=None):
    subprocess.run(
        [str(item) for item in command],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
    )


def build_release():
    names = release_artifact_names()

    _reset_scoped_directory(
        BUILD_ROOT,
        PROJECT_ROOT / "build",
    )
    _reset_scoped_directory(
        DIST_ROOT,
        PROJECT_ROOT / "dist",
    )
    _reset_scoped_directory(
        RELEASE_ROOT,
        PROJECT_ROOT / "release",
    )

    package_database = (
        BUILD_ROOT
        / "package_input"
        / "database"
        / "redbox_os.db"
    )
    database_status = (
        create_fresh_install_database(
            package_database
        )
    )

    environment = os.environ.copy()
    environment["REDBOX_PACKAGED_DB"] = str(
        package_database.resolve()
    )

    _run(
        (
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--workpath",
            BUILD_ROOT / "pyinstaller",
            "--distpath",
            DIST_ROOT,
            PROJECT_ROOT / "REDBOX_OS.spec",
        ),
        environment=environment,
    )

    app_path = DIST_ROOT / names["app"]
    if not app_path.is_dir():
        raise RuntimeError(
            f"Uygulama paketi oluşmadı: {app_path}"
        )

    dmg_path = RELEASE_ROOT / names["dmg"]

    with tempfile.TemporaryDirectory(
        prefix="redbox_macos_release_"
    ) as temp:
        local_root = Path(temp)
        dmg_stage = local_root / "dmg_stage"
        dmg_stage.mkdir()

        signed_app = dmg_stage / names["app"]
        _run((
            "/usr/bin/ditto",
            app_path,
            signed_app,
        ))
        _run((
            "/usr/bin/xattr",
            "-crs",
            signed_app,
        ))
        _run((
            "/usr/bin/codesign",
            "--force",
            "--deep",
            "--sign",
            "-",
            signed_app,
        ))
        _run((
            "/usr/bin/codesign",
            "--verify",
            "--deep",
            "--strict",
            signed_app,
        ))

        (dmg_stage / "Applications").symlink_to(
            "/Applications"
        )

        documents_dir = dmg_stage / "Belgeler"
        documents_dir.mkdir()
        for document_path in release_document_paths():
            shutil.copy2(
                document_path,
                documents_dir / document_path.name,
            )

        local_dmg = local_root / names["dmg"]
        _run((
            "/usr/bin/hdiutil",
            "create",
            "-volname",
            APP_DISPLAY_NAME,
            "-srcfolder",
            dmg_stage,
            "-ov",
            "-format",
            "UDZO",
            local_dmg,
        ))
        _run((
            "/usr/bin/hdiutil",
            "verify",
            local_dmg,
        ))

        shutil.copy2(local_dmg, dmg_path)

    manifest_path = (
        RELEASE_ROOT / names["manifest"]
    )
    manifest = {
        "format": "REDBOX_RELEASE_V1",
        "product": APP_DISPLAY_NAME,
        "version": APP_VERSION,
        "build": APP_BUILD,
        "bundle_identifier": BUNDLE_IDENTIFIER,
        "created_at": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),
        "dmg": {
            "filename": dmg_path.name,
            "sha256": _sha256(dmg_path),
            "size_bytes": dmg_path.stat().st_size,
        },
        "fresh_database": {
            "schema_version": (
                database_status[
                    "schema_version"
                ]
            ),
            "sha256": database_status["sha256"],
            "protected_counts": (
                database_status[
                    "protected_counts"
                ]
            ),
        },
        "signing": {
            "mode": "AD_HOC",
            "notarized": False,
        },
    }
    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "app": app_path,
        "dmg": dmg_path,
        "manifest": manifest_path,
        "database": database_status,
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "REDBOX OS macOS .app ve DMG üretir."
        )
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Kontrollü temiz dağıtımı üret.",
    )
    args = parser.parse_args()

    if not args.build:
        parser.error(
            "Dağıtım üretmek için --build gereklidir."
        )

    result = build_release()
    print("APP      :", result["app"])
    print("DMG      :", result["dmg"])
    print("MANIFEST :", result["manifest"])


if __name__ == "__main__":
    main()

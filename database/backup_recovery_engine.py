import hashlib
import json
import os
import sqlite3
import uuid
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from database.audit_engine import denetim_kaydi_ekle
from database.migrations import run_migrations


BACKUP_FORMAT = "REDBOX_BACKUP_V1"
ALLOWED_BACKUP_TYPES = {
    "MANUEL",
    "OTOMATIK",
    "GERI_YUKLEME_ONCESI",
}


class BackupRecoveryError(RuntimeError):
    pass


class BackupValidationError(BackupRecoveryError):
    pass


def _sha256_file(path):
    digest = hashlib.sha256()

    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def _readonly_connection(database_path):
    database_path = Path(database_path).resolve()

    if not database_path.is_file():
        raise FileNotFoundError(
            f"Veritabanı bulunamadı: {database_path}"
        )

    connection = sqlite3.connect(
        f"{database_path.as_uri()}?mode=ro",
        uri=True,
    )
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _normalized_datetime(value=None):
    if value is None:
        return datetime.now().astimezone()

    parsed = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(str(value))
    )

    if parsed.tzinfo is None:
        parsed = parsed.astimezone()

    return parsed


def _atomic_json_write(path, payload):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.unlink(missing_ok=True)

    try:
        temporary.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def veritabani_durumunu_getir(database_path):
    database_path = Path(database_path)
    connection = _readonly_connection(database_path)

    try:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
        schema_version = connection.execute(
            "PRAGMA user_version"
        ).fetchone()[0]
    finally:
        connection.close()

    return {
        "integrity": integrity,
        "foreign_key_violations": len(foreign_keys),
        "schema_version": schema_version,
        "sha256": _sha256_file(database_path),
        "size_bytes": database_path.stat().st_size,
    }


def _validate_database_health(status, label):
    if status["integrity"] != "ok":
        raise BackupValidationError(
            f"{label} bütünlük kontrolü başarısız: "
            f"{status['integrity']}"
        )

    if status["foreign_key_violations"]:
        raise BackupValidationError(
            f"{label} foreign-key ihlali içeriyor: "
            f"{status['foreign_key_violations']}"
        )


def dogrulanmis_yedek_olustur(
    source_path,
    backup_dir,
    *,
    yedek_turu,
    kullanici=None,
    oturum_id=None,
    simdi=None,
):
    source_path = Path(source_path)
    backup_dir = Path(backup_dir)
    backup_type = str(yedek_turu).strip().upper()

    if backup_type not in ALLOWED_BACKUP_TYPES:
        raise ValueError(
            f"Geçersiz yedek türü: {backup_type}"
        )

    source_status = veritabani_durumunu_getir(source_path)
    _validate_database_health(
        source_status,
        "Kaynak veritabanı",
    )

    created_at = _normalized_datetime(simdi)
    backup_dir.mkdir(parents=True, exist_ok=True)

    stem = (
        f"redbox_os_{backup_type.lower()}_"
        f"{created_at.strftime('%Y%m%d_%H%M%S')}"
    )
    backup_path = backup_dir / f"{stem}.db"
    manifest_path = backup_dir / f"{stem}.manifest.json"
    pending_path = backup_dir / f".{stem}.pending.db"

    if backup_path.exists() or manifest_path.exists():
        raise FileExistsError(
            f"Aynı zaman damgalı yedek zaten var: {stem}"
        )

    pending_path.unlink(missing_ok=True)
    source_connection = _readonly_connection(source_path)
    target_connection = None

    try:
        target_connection = sqlite3.connect(str(pending_path))
        source_connection.backup(target_connection)
        target_connection.commit()
    except Exception:
        pending_path.unlink(missing_ok=True)
        raise
    finally:
        if target_connection is not None:
            target_connection.close()
        source_connection.close()

    try:
        pending_status = veritabani_durumunu_getir(
            pending_path
        )
        _validate_database_health(
            pending_status,
            "Oluşturulan yedek",
        )

        os.replace(pending_path, backup_path)

        backup_status = veritabani_durumunu_getir(
            backup_path
        )
        _validate_database_health(
            backup_status,
            "Oluşturulan yedek",
        )

        manifest = {
            "format": BACKUP_FORMAT,
            "created_at": created_at.isoformat(),
            "backup_type": backup_type,
            "database_file": backup_path.name,
            "database_sha256": backup_status["sha256"],
            "database_size_bytes": backup_status["size_bytes"],
            "schema_version": backup_status["schema_version"],
            "integrity": backup_status["integrity"],
            "foreign_key_violations": backup_status[
                "foreign_key_violations"
            ],
            "source_file": source_path.name,
            "operator_username": (
                (kullanici or {}).get("kullanici_adi")
            ),
            "session_id": oturum_id,
        }

        _atomic_json_write(manifest_path, manifest)
    except Exception:
        pending_path.unlink(missing_ok=True)
        backup_path.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)
        raise

    return {
        "backup_path": str(backup_path),
        "manifest_path": str(manifest_path),
        "backup_type": backup_type,
        "created_at": created_at.isoformat(),
        "sha256": backup_status["sha256"],
        "schema_version": backup_status["schema_version"],
        "integrity": backup_status["integrity"],
        "foreign_key_violations": backup_status[
            "foreign_key_violations"
        ],
        "size_bytes": backup_status["size_bytes"],
    }


def yedegi_dogrula(backup_path, manifest_path=None):
    backup_path = Path(backup_path)

    if manifest_path is None:
        manifest_path = backup_path.with_name(
            f"{backup_path.stem}.manifest.json"
        )

    manifest_path = Path(manifest_path)

    if not manifest_path.is_file():
        raise BackupValidationError(
            "Yedek manifest dosyası bulunamadı."
        )

    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupValidationError(
            "Yedek manifest dosyası okunamadı."
        ) from exc

    if manifest.get("format") != BACKUP_FORMAT:
        raise BackupValidationError(
            "Desteklenmeyen yedek manifest biçimi."
        )

    if manifest.get("database_file") != backup_path.name:
        raise BackupValidationError(
            "Manifest ile yedek dosya adı eşleşmiyor."
        )

    actual_sha = _sha256_file(backup_path)

    if manifest.get("database_sha256") != actual_sha:
        raise BackupValidationError(
            "Yedek SHA-256 doğrulaması başarısız."
        )

    status = veritabani_durumunu_getir(backup_path)
    _validate_database_health(status, "Yedek veritabanı")

    if manifest.get("schema_version") != status["schema_version"]:
        raise BackupValidationError(
            "Manifest ile yedek şema sürümü eşleşmiyor."
        )

    if manifest.get("database_size_bytes") != status["size_bytes"]:
        raise BackupValidationError(
            "Manifest ile yedek dosya boyutu eşleşmiyor."
        )

    return {
        "valid": True,
        "backup_path": str(backup_path),
        "manifest_path": str(manifest_path),
        "backup_type": manifest.get("backup_type"),
        "created_at": manifest.get("created_at"),
        "sha256": actual_sha,
        "schema_version": status["schema_version"],
        "integrity": status["integrity"],
        "foreign_key_violations": status[
            "foreign_key_violations"
        ],
        "size_bytes": status["size_bytes"],
    }


def yedekleme_politikasini_getir(conn):
    row = conn.execute("""
        SELECT
            aktif,
            siklik_saat,
            saklama_adedi,
            son_otomatik_yedek_zamani,
            sonraki_otomatik_yedek_zamani,
            kayit_zamani,
            guncelleme_zamani
        FROM yedekleme_politikasi
        WHERE id = 1
    """).fetchone()

    if row is None:
        raise BackupRecoveryError(
            "Yedekleme politikası bulunamadı."
        )

    return {
        "aktif": bool(row[0]),
        "siklik_saat": row[1],
        "saklama_adedi": row[2],
        "son_otomatik_yedek_zamani": row[3],
        "sonraki_otomatik_yedek_zamani": row[4],
        "kayit_zamani": row[5],
        "guncelleme_zamani": row[6],
    }


def otomatik_yedek_gerekli_mi(conn, simdi=None):
    policy = yedekleme_politikasini_getir(conn)
    now = _normalized_datetime(simdi)

    if not policy["aktif"]:
        return {
            "gerekli": False,
            "neden_kodu": "POLITIKA_PASIF",
            "simdi": now.isoformat(),
            "sonraki_yedek_zamani": (
                policy["sonraki_otomatik_yedek_zamani"]
            ),
        }

    next_value = policy[
        "sonraki_otomatik_yedek_zamani"
    ]

    if next_value:
        next_time = _normalized_datetime(next_value)
    else:
        last_value = policy[
            "son_otomatik_yedek_zamani"
        ]

        if last_value:
            next_time = (
                _normalized_datetime(last_value)
                + timedelta(
                    hours=policy["siklik_saat"]
                )
            )
        else:
            next_time = now

    required = now >= next_time

    return {
        "gerekli": required,
        "neden_kodu": (
            "YEDEK_ZAMANI_GELDI"
            if required
            else "HENUZ_ZAMANI_DEGIL"
        ),
        "simdi": now.isoformat(),
        "sonraki_yedek_zamani": next_time.isoformat(),
    }


def yedekleme_politikasini_guncelle(
    conn,
    *,
    aktif,
    siklik_saat,
    saklama_adedi,
    kullanici=None,
    oturum_id=None,
    simdi=None,
):
    active_value = 1 if bool(aktif) else 0

    try:
        frequency = int(siklik_saat)
        retention = int(saklama_adedi)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Yedek sıklığı ve saklama adedi tam sayı olmalıdır."
        ) from exc

    if not 1 <= frequency <= 168:
        raise ValueError(
            "Yedek sıklığı 1 ile 168 saat arasında olmalıdır."
        )

    if not 1 <= retention <= 100:
        raise ValueError(
            "Saklama adedi 1 ile 100 arasında olmalıdır."
        )

    old_policy = yedekleme_politikasini_getir(conn)
    now = _normalized_datetime(simdi)
    next_time = (
        now + timedelta(hours=frequency)
        if active_value
        else None
    )

    try:
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.execute("""
            UPDATE yedekleme_politikasi
            SET
                aktif = ?,
                siklik_saat = ?,
                saklama_adedi = ?,
                sonraki_otomatik_yedek_zamani = ?,
                guncelleme_zamani = ?
            WHERE id = 1
        """, (
            active_value,
            frequency,
            retention,
            (
                next_time.isoformat()
                if next_time is not None
                else None
            ),
            now.isoformat(),
        ))

        if cursor.rowcount != 1:
            raise BackupRecoveryError(
                "Yedekleme politikası güncellenemedi."
            )

        new_policy = yedekleme_politikasini_getir(conn)

        denetim_kaydi_ekle(
            conn,
            modul="SISTEM",
            islem="GUNCELLEME",
            kullanici=kullanici,
            kayit_turu="yedekleme_politikasi",
            kayit_id=1,
            aciklama=(
                "Otomatik yedekleme politikası güncellendi."
            ),
            eski_deger={
                "aktif": old_policy["aktif"],
                "siklik_saat": old_policy["siklik_saat"],
                "saklama_adedi": old_policy["saklama_adedi"],
            },
            yeni_deger={
                "aktif": new_policy["aktif"],
                "siklik_saat": new_policy["siklik_saat"],
                "saklama_adedi": new_policy["saklama_adedi"],
            },
            oturum_id=oturum_id,
            olay_zamani=now.strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return new_policy


def _connection_database_path(conn):
    rows = conn.execute("PRAGMA database_list").fetchall()

    for row in rows:
        if row[1] == "main":
            return Path(row[2]).resolve()

    raise BackupRecoveryError(
        "Ana veritabanı bağlantı yolu bulunamadı."
    )


def _created_backup_files(result):
    return (
        Path(result["backup_path"]),
        Path(result["manifest_path"]),
    )


def _created_backup_files_remove(result):
    for path in _created_backup_files(result):
        path.unlink(missing_ok=True)


def otomatik_yedeklemeyi_calistir(
    conn,
    source_path,
    backup_dir,
    *,
    kullanici=None,
    oturum_id=None,
    simdi=None,
):
    source_path = Path(source_path).resolve()
    connected_path = _connection_database_path(conn)

    if source_path != connected_path:
        raise BackupRecoveryError(
            "Yedek kaydı ile kaynak veritabanı "
            "aynı bağlantıyı kullanmalıdır."
        )

    decision = otomatik_yedek_gerekli_mi(
        conn,
        simdi=simdi,
    )

    if not decision["gerekli"]:
        return {
            "calisti": False,
            "neden_kodu": decision["neden_kodu"],
            "sonraki_yedek_zamani": decision[
                "sonraki_yedek_zamani"
            ],
        }

    now = _normalized_datetime(simdi)
    result = dogrulanmis_yedek_olustur(
        source_path,
        backup_dir,
        yedek_turu="OTOMATIK",
        kullanici=kullanici,
        oturum_id=oturum_id,
        simdi=now,
    )
    policy = yedekleme_politikasini_getir(conn)
    next_time = now + timedelta(
        hours=policy["siklik_saat"]
    )
    backup_uuid = uuid.uuid4().hex

    try:
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.execute("""
            INSERT INTO yedekleme_kayitlari (
                yedek_uuid,
                yedek_turu,
                dosya_adi,
                manifest_dosya_adi,
                database_sha256,
                boyut_byte,
                schema_version,
                durum,
                olusturma_zamani,
                dogrulama_zamani,
                kullanici_id,
                oturum_id
            )
            VALUES (
                ?,
                'OTOMATIK',
                ?,
                ?,
                ?,
                ?,
                ?,
                'BASARILI',
                ?,
                ?,
                ?,
                ?
            )
        """, (
            backup_uuid,
            Path(result["backup_path"]).name,
            Path(result["manifest_path"]).name,
            result["sha256"],
            result["size_bytes"],
            result["schema_version"],
            now.isoformat(),
            now.isoformat(),
            (kullanici or {}).get(
                "hesap_id",
                (kullanici or {}).get("id"),
            ),
            oturum_id,
        ))

        conn.execute("""
            UPDATE yedekleme_politikasi
            SET
                son_otomatik_yedek_zamani = ?,
                sonraki_otomatik_yedek_zamani = ?,
                guncelleme_zamani = ?
            WHERE id = 1
        """, (
            now.isoformat(),
            next_time.isoformat(),
            now.isoformat(),
        ))

        denetim_kaydi_ekle(
            conn,
            modul="SISTEM",
            islem="YEDEKLEME",
            kullanici=kullanici,
            kayit_turu="database_backup",
            kayit_id=cursor.lastrowid,
            aciklama=(
                "Doğrulanmış otomatik veritabanı "
                "yedeği oluşturuldu."
            ),
            yeni_deger={
                "yedek_uuid": backup_uuid,
                "yedek_turu": "OTOMATIK",
                "dosya_adi": Path(
                    result["backup_path"]
                ).name,
                "database_sha256": result["sha256"],
                "butunluk": "OK",
            },
            oturum_id=oturum_id,
            olay_zamani=now.strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        _created_backup_files_remove(result)
        raise

    return {
        **result,
        "calisti": True,
        "neden_kodu": "OTOMATIK_YEDEK_TAMAMLANDI",
        "yedek_uuid": backup_uuid,
        "kayit_id": cursor.lastrowid,
        "sonraki_yedek_zamani": next_time.isoformat(),
    }


def _safe_recorded_file(backup_dir, file_name):
    backup_dir = Path(backup_dir).resolve()
    normalized_name = Path(str(file_name)).name

    if normalized_name != str(file_name):
        raise BackupRecoveryError(
            "Yedek kaydında güvenli olmayan dosya adı var."
        )

    candidate = (backup_dir / normalized_name).resolve()

    if candidate.parent != backup_dir:
        raise BackupRecoveryError(
            "Yedek dosyası izin verilen dizinin dışında."
        )

    return candidate


def saklama_politikasini_uygula(
    conn,
    backup_dir,
    *,
    kullanici=None,
    oturum_id=None,
    simdi=None,
):
    backup_dir = Path(backup_dir).resolve()
    policy = yedekleme_politikasini_getir(conn)
    retention = policy["saklama_adedi"]
    now = _normalized_datetime(simdi)

    rows = conn.execute("""
        SELECT
            id,
            yedek_uuid,
            dosya_adi,
            manifest_dosya_adi
        FROM yedekleme_kayitlari
        WHERE
            yedek_turu = 'OTOMATIK'
            AND durum = 'BASARILI'
        ORDER BY
            olusturma_zamani DESC,
            id DESC
        LIMIT -1 OFFSET ?
    """, (retention,)).fetchall()

    if not rows:
        return {
            "uygulandi": True,
            "silinen_yedek_sayisi": 0,
            "saklama_adedi": retention,
        }

    quarantine = (
        backup_dir
        / ".retention_pending"
        / uuid.uuid4().hex
    )
    moved = []

    try:
        quarantine.mkdir(
            parents=True,
            exist_ok=False,
        )

        for row in rows:
            backup_path = _safe_recorded_file(
                backup_dir,
                row[2],
            )
            manifest_path = _safe_recorded_file(
                backup_dir,
                row[3],
            )

            if not backup_path.is_file():
                raise BackupRecoveryError(
                    f"Kayıtlı yedek dosyası bulunamadı: "
                    f"{backup_path.name}"
                )

            if not manifest_path.is_file():
                raise BackupRecoveryError(
                    f"Kayıtlı manifest bulunamadı: "
                    f"{manifest_path.name}"
                )

            for original in (
                backup_path,
                manifest_path,
            ):
                temporary = quarantine / original.name
                os.replace(original, temporary)
                moved.append((original, temporary))

        conn.execute("BEGIN IMMEDIATE")

        for row in rows:
            conn.execute("""
                UPDATE yedekleme_kayitlari
                SET
                    durum = 'SILINDI',
                    silinme_zamani = ?
                WHERE
                    id = ?
                    AND durum = 'BASARILI'
            """, (
                now.isoformat(),
                row[0],
            ))

        denetim_kaydi_ekle(
            conn,
            modul="SISTEM",
            islem="SILME",
            kullanici=kullanici,
            kayit_turu="backup_retention",
            aciklama=(
                "Otomatik yedek saklama politikası "
                "kontrollü olarak uygulandı."
            ),
            yeni_deger={
                "saklama_adedi": retention,
                "silinen_yedek_sayisi": len(rows),
                "yedek_uuid_listesi": [
                    row[1] for row in rows
                ],
            },
            oturum_id=oturum_id,
            olay_zamani=now.strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
        )

        conn.commit()
    except Exception:
        conn.rollback()

        for original, temporary in reversed(moved):
            if temporary.exists():
                original.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                os.replace(temporary, original)

        if quarantine.exists():
            shutil.rmtree(quarantine)

        raise

    for _original, temporary in moved:
        temporary.unlink(missing_ok=True)

    if quarantine.exists():
        quarantine.rmdir()

    pending_root = quarantine.parent

    if pending_root.exists() and not any(
        pending_root.iterdir()
    ):
        pending_root.rmdir()

    return {
        "uygulandi": True,
        "silinen_yedek_sayisi": len(rows),
        "saklama_adedi": retention,
        "silinen_yedek_uuid_listesi": [
            row[1] for row in rows
        ],
    }


RESTORE_REQUEST_FORMAT = "REDBOX_RESTORE_REQUEST_V1"


def _sqlite_database_copy(source_path, target_path):
    source_path = Path(source_path)
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.unlink(missing_ok=True)

    source_connection = _readonly_connection(source_path)
    target_connection = None

    try:
        target_connection = sqlite3.connect(
            str(target_path)
        )
        source_connection.backup(target_connection)
        target_connection.commit()
    except Exception:
        target_path.unlink(missing_ok=True)
        raise
    finally:
        if target_connection is not None:
            target_connection.close()
        source_connection.close()

    return target_path


def geri_yuklemeyi_hazirla(
    live_path,
    selected_backup_path,
    selected_manifest_path,
    backup_dir,
    recovery_dir,
    *,
    kullanici=None,
    oturum_id=None,
    simdi=None,
):
    live_path = Path(live_path).resolve()
    selected_backup_path = Path(
        selected_backup_path
    ).resolve()
    selected_manifest_path = Path(
        selected_manifest_path
    ).resolve()
    backup_dir = Path(backup_dir).resolve()
    recovery_dir = Path(recovery_dir).resolve()
    now = _normalized_datetime(simdi)

    live_status = veritabani_durumunu_getir(live_path)
    _validate_database_health(
        live_status,
        "Canlı veritabanı",
    )

    selected_validation = yedegi_dogrula(
        selected_backup_path,
        selected_manifest_path,
    )

    recovery_dir.mkdir(parents=True, exist_ok=True)
    request_path = recovery_dir / "restore_request.json"
    pending_path = recovery_dir / "restore_pending.db"

    if request_path.exists() or pending_path.exists():
        raise BackupRecoveryError(
            "Tamamlanmamış bir geri yükleme isteği var."
        )

    safety = None

    try:
        safety = dogrulanmis_yedek_olustur(
            live_path,
            backup_dir,
            yedek_turu="GERI_YUKLEME_ONCESI",
            kullanici=kullanici,
            oturum_id=oturum_id,
            simdi=now,
        )

        _sqlite_database_copy(
            selected_backup_path,
            pending_path,
        )

        run_migrations(pending_path)

        pending_status = veritabani_durumunu_getir(
            pending_path
        )
        _validate_database_health(
            pending_status,
            "Bekleyen geri yükleme kopyası",
        )

        request = {
            "format": RESTORE_REQUEST_FORMAT,
            "request_uuid": uuid.uuid4().hex,
            "created_at": now.isoformat(),
            "live_database_file": live_path.name,
            "live_sha256_before": live_status["sha256"],
            "live_schema_version_before": live_status[
                "schema_version"
            ],
            "selected_backup_file": (
                selected_backup_path.name
            ),
            "selected_backup_sha256": (
                selected_validation["sha256"]
            ),
            "pending_file": pending_path.name,
            "pending_sha256": pending_status["sha256"],
            "pending_schema_version": pending_status[
                "schema_version"
            ],
            "safety_backup_file": Path(
                safety["backup_path"]
            ).name,
            "safety_manifest_file": Path(
                safety["manifest_path"]
            ).name,
            "safety_backup_sha256": safety["sha256"],
            "operator_username": (
                (kullanici or {}).get("kullanici_adi")
            ),
            "operator_account_id": (
                (kullanici or {}).get(
                    "hesap_id",
                    (kullanici or {}).get("id"),
                )
            ),
            "session_id": oturum_id,
            "status": "HAZIRLANDI",
        }

        _atomic_json_write(request_path, request)
    except Exception:
        pending_path.unlink(missing_ok=True)
        request_path.unlink(missing_ok=True)

        if safety is not None:
            _created_backup_files_remove(safety)

        raise

    live_after = veritabani_durumunu_getir(live_path)

    if live_after["sha256"] != live_status["sha256"]:
        pending_path.unlink(missing_ok=True)
        request_path.unlink(missing_ok=True)
        _created_backup_files_remove(safety)

        raise BackupRecoveryError(
            "Hazırlık sırasında canlı veritabanı değişti."
        )

    return {
        "hazirlandi": True,
        "request_path": str(request_path),
        "pending_path": str(pending_path),
        "safety_backup_path": safety["backup_path"],
        "safety_manifest_path": safety["manifest_path"],
        "live_sha256_before": live_status["sha256"],
        "selected_backup_sha256": selected_validation[
            "sha256"
        ],
        "pending_sha256": pending_status["sha256"],
        "pending_schema_version": pending_status[
            "schema_version"
        ],
    }


def _safe_recovery_file(recovery_dir, file_name):
    recovery_dir = Path(recovery_dir).resolve()
    normalized_name = Path(str(file_name)).name

    if normalized_name != str(file_name):
        raise BackupRecoveryError(
            "Geri yükleme isteğinde güvenli olmayan "
            "dosya adı var."
        )

    candidate = (recovery_dir / normalized_name).resolve()

    if candidate.parent != recovery_dir:
        raise BackupRecoveryError(
            "Geri yükleme dosyası izin verilen "
            "dizinin dışında."
        )

    return candidate


def _restore_operator_for_database(conn, request):
    account_id = request.get("operator_account_id")
    valid_account_id = None

    if account_id is not None:
        row = conn.execute(
            """
            SELECT id
            FROM kullanici_hesaplari
            WHERE id = ?
            """,
            (account_id,),
        ).fetchone()

        if row is not None:
            valid_account_id = row[0]

    return {
        "hesap_id": valid_account_id,
        "kullanici_adi": request.get(
            "operator_username"
        ),
        "ad_soyad": None,
        "personel_id": None,
    }


def bekleyen_geri_yuklemeyi_uygula(
    live_path,
    backup_dir,
    recovery_dir,
    *,
    simdi=None,
):
    live_path = Path(live_path).resolve()
    backup_dir = Path(backup_dir).resolve()
    recovery_dir = Path(recovery_dir).resolve()
    request_path = recovery_dir / "restore_request.json"

    if not request_path.is_file():
        return {
            "uygulandi": False,
            "neden_kodu": "BEKLEYEN_ISTEK_YOK",
        }

    try:
        request = json.loads(
            request_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupValidationError(
            "Geri yükleme istek dosyası okunamadı."
        ) from exc

    if request.get("format") != RESTORE_REQUEST_FORMAT:
        raise BackupValidationError(
            "Desteklenmeyen geri yükleme istek biçimi."
        )

    if request.get("status") != "HAZIRLANDI":
        raise BackupValidationError(
            "Geri yükleme isteği hazır durumda değil."
        )

    if request.get("live_database_file") != live_path.name:
        raise BackupValidationError(
            "Geri yükleme isteği canlı DB ile eşleşmiyor."
        )

    current_status = veritabani_durumunu_getir(
        live_path
    )
    _validate_database_health(
        current_status,
        "Canlı veritabanı",
    )

    if current_status["sha256"] != request.get(
        "live_sha256_before"
    ):
        raise BackupValidationError(
            "Canlı veritabanı hazırlıktan sonra değişmiş."
        )

    pending_path = _safe_recovery_file(
        recovery_dir,
        request.get("pending_file"),
    )
    safety_backup_path = _safe_recorded_file(
        backup_dir,
        request.get("safety_backup_file"),
    )
    safety_manifest_path = _safe_recorded_file(
        backup_dir,
        request.get("safety_manifest_file"),
    )

    safety_validation = yedegi_dogrula(
        safety_backup_path,
        safety_manifest_path,
    )
    pending_status = veritabani_durumunu_getir(
        pending_path
    )
    _validate_database_health(
        pending_status,
        "Bekleyen geri yükleme kopyası",
    )

    if pending_status["sha256"] != request.get(
        "pending_sha256"
    ):
        raise BackupValidationError(
            "Bekleyen geri yükleme SHA-256 "
            "doğrulaması başarısız."
        )

    now = _normalized_datetime(simdi)
    replaced = False
    audit_connection = None
    safety_uuid = uuid.uuid4().hex

    try:
        os.replace(pending_path, live_path)
        replaced = True

        restored_status = veritabani_durumunu_getir(
            live_path
        )
        _validate_database_health(
            restored_status,
            "Geri yüklenen canlı veritabanı",
        )

        audit_connection = sqlite3.connect(
            str(live_path)
        )
        audit_connection.execute(
            "PRAGMA foreign_keys = ON"
        )
        audit_connection.execute("BEGIN IMMEDIATE")

        operator = _restore_operator_for_database(
            audit_connection,
            request,
        )

        safety_cursor = audit_connection.execute("""
            INSERT INTO yedekleme_kayitlari (
                yedek_uuid,
                yedek_turu,
                dosya_adi,
                manifest_dosya_adi,
                database_sha256,
                boyut_byte,
                schema_version,
                durum,
                olusturma_zamani,
                dogrulama_zamani,
                kullanici_id,
                oturum_id
            )
            VALUES (
                ?,
                'GERI_YUKLEME_ONCESI',
                ?,
                ?,
                ?,
                ?,
                ?,
                'BASARILI',
                ?,
                ?,
                ?,
                ?
            )
        """, (
            safety_uuid,
            safety_backup_path.name,
            safety_manifest_path.name,
            safety_validation["sha256"],
            safety_validation["size_bytes"],
            safety_validation["schema_version"],
            request["created_at"],
            now.isoformat(),
            operator["hesap_id"],
            request.get("session_id"),
        ))

        restore_cursor = audit_connection.execute("""
            INSERT INTO geri_yukleme_kayitlari (
                geri_yukleme_uuid,
                kaynak_dosya_adi,
                kaynak_sha256,
                emniyet_yedegi_dosya_adi,
                emniyet_yedegi_sha256,
                onceki_schema_version,
                sonraki_schema_version,
                durum,
                baslangic_zamani,
                tamamlanma_zamani,
                kullanici_id,
                oturum_id
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                'TAMAMLANDI',
                ?,
                ?,
                ?,
                ?
            )
        """, (
            request["request_uuid"],
            request["selected_backup_file"],
            request["selected_backup_sha256"],
            safety_backup_path.name,
            safety_validation["sha256"],
            request["live_schema_version_before"],
            restored_status["schema_version"],
            request["created_at"],
            now.isoformat(),
            operator["hesap_id"],
            request.get("session_id"),
        ))

        denetim_kaydi_ekle(
            audit_connection,
            modul="SISTEM",
            islem="GERI_YUKLEME",
            kullanici=operator,
            kayit_turu="database_restore",
            kayit_id=restore_cursor.lastrowid,
            aciklama=(
                "Doğrulanmış veritabanı yedeği "
                "güvenli başlangıç aşamasında geri yüklendi."
            ),
            yeni_deger={
                "kaynak_dosya": request[
                    "selected_backup_file"
                ],
                "kaynak_sha256": request[
                    "selected_backup_sha256"
                ],
                "emniyet_yedegi": (
                    safety_backup_path.name
                ),
                "emniyet_yedegi_kayit_id": (
                    safety_cursor.lastrowid
                ),
                "butunluk": "OK",
            },
            oturum_id=request.get("session_id"),
            olay_zamani=now.strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
        )

        audit_connection.commit()
        audit_connection.close()
        audit_connection = None
    except Exception as exc:
        if audit_connection is not None:
            audit_connection.rollback()
            audit_connection.close()
            audit_connection = None

        if replaced:
            rollback_pending = (
                recovery_dir / "rollback_pending.db"
            )
            rollback_pending.unlink(missing_ok=True)

            try:
                _sqlite_database_copy(
                    safety_backup_path,
                    rollback_pending,
                )
                os.replace(
                    rollback_pending,
                    live_path,
                )

                rollback_status = (
                    veritabani_durumunu_getir(
                        live_path
                    )
                )
                _validate_database_health(
                    rollback_status,
                    "Geri alınan canlı veritabanı",
                )

                if (
                    rollback_status["schema_version"]
                    != request["live_schema_version_before"]
                ):
                    raise BackupRecoveryError(
                        "Emniyet yedeğine dönüş şema "
                        "doğrulaması başarısız."
                    )
            except Exception as rollback_exc:
                raise BackupRecoveryError(
                    "Geri yükleme ve emniyet geri dönüşü "
                    "başarısız."
                ) from rollback_exc

        raise BackupRecoveryError(
            "Geri yükleme uygulanamadı; canlı veritabanı "
            "emniyet yedeğine döndürüldü."
        ) from exc

    final_status = veritabani_durumunu_getir(
        live_path
    )
    request_path.unlink(missing_ok=True)

    return {
        "uygulandi": True,
        "neden_kodu": "GERI_YUKLEME_TAMAMLANDI",
        "request_uuid": request["request_uuid"],
        "safety_backup_path": str(
            safety_backup_path
        ),
        "schema_version": final_status[
            "schema_version"
        ],
        "integrity": final_status["integrity"],
        "foreign_key_violations": final_status[
            "foreign_key_violations"
        ],
        "sha256": final_status["sha256"],
    }


def manuel_yedek_olustur(
    conn,
    source_path,
    backup_dir,
    *,
    kullanici=None,
    oturum_id=None,
    simdi=None,
):
    source_path = Path(source_path).resolve()
    connected_path = _connection_database_path(conn)

    if source_path != connected_path:
        raise BackupRecoveryError(
            "Yedek kaydı ile kaynak veritabanı "
            "aynı bağlantıyı kullanmalıdır."
        )

    now = _normalized_datetime(simdi)
    result = dogrulanmis_yedek_olustur(
        source_path,
        backup_dir,
        yedek_turu="MANUEL",
        kullanici=kullanici,
        oturum_id=oturum_id,
        simdi=now,
    )
    backup_uuid = uuid.uuid4().hex

    try:
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.execute("""
            INSERT INTO yedekleme_kayitlari (
                yedek_uuid,
                yedek_turu,
                dosya_adi,
                manifest_dosya_adi,
                database_sha256,
                boyut_byte,
                schema_version,
                durum,
                olusturma_zamani,
                dogrulama_zamani,
                kullanici_id,
                oturum_id
            )
            VALUES (
                ?,
                'MANUEL',
                ?,
                ?,
                ?,
                ?,
                ?,
                'BASARILI',
                ?,
                ?,
                ?,
                ?
            )
        """, (
            backup_uuid,
            Path(result["backup_path"]).name,
            Path(result["manifest_path"]).name,
            result["sha256"],
            result["size_bytes"],
            result["schema_version"],
            now.isoformat(),
            now.isoformat(),
            (kullanici or {}).get(
                "hesap_id",
                (kullanici or {}).get("id"),
            ),
            oturum_id,
        ))

        denetim_kaydi_ekle(
            conn,
            modul="SISTEM",
            islem="YEDEKLEME",
            kullanici=kullanici,
            kayit_turu="database_backup",
            kayit_id=cursor.lastrowid,
            aciklama=(
                "Doğrulanmış manuel veritabanı "
                "yedeği oluşturuldu."
            ),
            yeni_deger={
                "yedek_uuid": backup_uuid,
                "yedek_turu": "MANUEL",
                "dosya_adi": Path(
                    result["backup_path"]
                ).name,
                "database_sha256": result["sha256"],
                "butunluk": "OK",
            },
            oturum_id=oturum_id,
            olay_zamani=now.strftime(
                "%d.%m.%Y %H:%M:%S"
            ),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        _created_backup_files_remove(result)
        raise

    return {
        **result,
        "yedek_uuid": backup_uuid,
        "kayit_id": cursor.lastrowid,
    }


def yedekleme_gecmisini_getir(conn, limit=20):
    try:
        normalized_limit = int(limit)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Yedek geçmişi limiti tam sayı olmalıdır."
        ) from exc

    if not 1 <= normalized_limit <= 200:
        raise ValueError(
            "Yedek geçmişi limiti 1 ile 200 "
            "arasında olmalıdır."
        )

    rows = conn.execute("""
        SELECT
            yedek_uuid,
            yedek_turu,
            dosya_adi,
            database_sha256,
            boyut_byte,
            schema_version,
            durum,
            olusturma_zamani,
            dogrulama_zamani,
            silinme_zamani
        FROM yedekleme_kayitlari
        ORDER BY olusturma_zamani DESC, id DESC
        LIMIT ?
    """, (normalized_limit,)).fetchall()

    return [
        {
            "yedek_uuid": row[0],
            "yedek_turu": row[1],
            "dosya_adi": row[2],
            "database_sha256": row[3],
            "boyut_byte": row[4],
            "schema_version": row[5],
            "durum": row[6],
            "olusturma_zamani": row[7],
            "dogrulama_zamani": row[8],
            "silinme_zamani": row[9],
        }
        for row in rows
    ]

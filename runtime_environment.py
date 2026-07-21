"""Paketlenmiş ve geliştirme çalışma ortamı altyapısı."""

import logging
import os
import sys
import threading
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from application_metadata import (
    APP_INTERNAL_NAME,
    VERSION_LABEL,
)


LOG_FILENAME = "redbox_os.log"
MAX_LOG_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 5


def runtime_directories(
    *,
    frozen,
    platform_name,
    home,
    project_root,
    environment,
):
    home = Path(home)
    project_root = Path(project_root)
    environment = dict(environment)

    if not frozen:
        data_dir = project_root / "database"
        log_dir = project_root / "logs"
    elif platform_name == "darwin":
        data_dir = (
            home
            / "Library"
            / "Application Support"
            / APP_INTERNAL_NAME
        )
        log_dir = data_dir / "logs"
    elif os.name == "nt":
        local_app_data = environment.get(
            "LOCALAPPDATA"
        )
        data_dir = (
            Path(local_app_data) / APP_INTERNAL_NAME
            if local_app_data
            else (
                home
                / "AppData"
                / "Local"
                / APP_INTERNAL_NAME
            )
        )
        log_dir = data_dir / "logs"
    else:
        xdg_data_home = environment.get(
            "XDG_DATA_HOME"
        )
        data_dir = (
            Path(xdg_data_home) / APP_INTERNAL_NAME
            if xdg_data_home
            else (
                home
                / ".local"
                / "share"
                / APP_INTERNAL_NAME
            )
        )
        state_home = environment.get(
            "XDG_STATE_HOME"
        )
        log_dir = (
            Path(state_home)
            / APP_INTERNAL_NAME
            / "logs"
            if state_home
            else data_dir / "logs"
        )

    return {
        "data": data_dir,
        "logs": log_dir,
        "crashes": log_dir / "crashes",
    }


def current_runtime_directories(project_root):
    return runtime_directories(
        frozen=bool(
            getattr(sys, "frozen", False)
        ),
        platform_name=sys.platform,
        home=Path.home(),
        project_root=Path(project_root),
        environment=os.environ,
    )


def configure_runtime_logging(log_dir):
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_FILENAME

    handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        )
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    logging.getLogger(
        "redbox.runtime"
    ).info("%s başlatılıyor", VERSION_LABEL)

    return {
        "log_path": log_path,
        "handlers": [handler],
    }


def _write_crash_report(
    crash_dir,
    exception_type,
    exception_value,
    exception_traceback,
    *,
    thread_name=None,
):
    crash_dir = Path(crash_dir)
    crash_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().astimezone()
    report_path = crash_dir / (
        "redbox_os_crash_"
        f"{timestamp:%Y%m%d_%H%M%S_%f}.log"
    )

    lines = [
        VERSION_LABEL,
        f"Zaman: {timestamp.isoformat()}",
    ]
    if thread_name:
        lines.append(f"Thread: {thread_name}")

    lines.extend([
        "",
        "Yakalanmamış hata:",
        "".join(
            traceback.format_exception(
                exception_type,
                exception_value,
                exception_traceback,
            )
        ),
    ])

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
    return report_path


def install_exception_hooks(crash_dir):
    crash_dir = Path(crash_dir)

    def sys_hook(
        exception_type,
        exception_value,
        exception_traceback,
    ):
        try:
            report = _write_crash_report(
                crash_dir,
                exception_type,
                exception_value,
                exception_traceback,
            )
            logging.getLogger(
                "redbox.crash"
            ).critical(
                "Yakalanmamış hata kaydedildi: %s",
                report.name,
            )
        except Exception:
            logging.getLogger(
                "redbox.crash"
            ).exception(
                "Çökme raporu oluşturulamadı"
            )

    def thread_hook(args):
        try:
            report = _write_crash_report(
                crash_dir,
                args.exc_type,
                args.exc_value,
                args.exc_traceback,
                thread_name=args.thread.name,
            )
            logging.getLogger(
                "redbox.crash"
            ).critical(
                "Thread hatası kaydedildi: %s",
                report.name,
            )
        except Exception:
            logging.getLogger(
                "redbox.crash"
            ).exception(
                "Thread çökme raporu oluşturulamadı"
            )

    sys.excepthook = sys_hook
    threading.excepthook = thread_hook

    return {
        "installed": True,
        "crash_dir": crash_dir,
    }

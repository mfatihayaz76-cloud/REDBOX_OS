# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_data_files

from application_metadata import (
    APP_BUILD,
    APP_VERSION,
    BUNDLE_IDENTIFIER,
)


block_cipher = None

packaged_database = os.environ.get(
    "REDBOX_PACKAGED_DB"
)

if not packaged_database:
    raise RuntimeError(
        "REDBOX_PACKAGED_DB temiz kurulum DB yolu gereklidir."
    )

datas = [
    (
        packaged_database,
        "database",
    ),
    (
        "licensing/public_keys.json",
        "licensing",
    ),
]

datas += collect_data_files(
    "customtkinter",
)

hiddenimports = [
    "cryptography",
    "cryptography.hazmat.primitives.serialization",
    "cryptography.hazmat.primitives.asymmetric.ed25519",
    "database.audit_engine",
    "database.backup_recovery_engine",
    "database.cleaning_engine",
    "database.company_profile_engine",
    "database.db",
    "database.licensing_engine",
    "database.finished_stock_engine",
    "database.migrations",
    "database.quality_engine",
    "database.raw_material_stock_engine",
    "database.report_engine",
    "database.stock_engine",
    "ui.backup_recovery_window",
    "ui.company_profile_window",
    "ui.controllers.dashboard_controller",
    "ui.license_center_window",
    "ui.login",
    "ui.order_calculator",
    "ui.pages.dashboard_page",
    "ui.quality",
    "ui.services.dashboard_service",
    "ui.services.order_calculator_service",
    "ui.services.production_service",
    "ui.services.quality_service",
    "ui.services.shipment_service",
    "ui.services.stock_service",
    "ui.system",
    "ui.widgets.critical_stock",
    "ui.widgets.dashboard_cards",
    "ui.widgets.quality_alerts",
    "ui.widgets.quick_actions",
    "ui.widgets.recent_activity",
]

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "unittest",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="REDBOX_OS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="REDBOX_OS",
)

app = BUNDLE(
    coll,
    name="REDBOX OS.app",
    icon="assets/REDBOX_OS.icns",
    bundle_identifier=BUNDLE_IDENTIFIER,
    version=APP_VERSION,
    info_plist={
        "CFBundleDisplayName": "REDBOX OS",
        "CFBundleName": "REDBOX OS",
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_BUILD,
        "NSHighResolutionCapable": True,
    },
)

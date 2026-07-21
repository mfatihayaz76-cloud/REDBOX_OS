# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_data_files


PROJECT_ROOT = os.path.abspath(".")

MANAGER_VERSION = "1.0.0"
MANAGER_BUILD = "1"
MANAGER_BUNDLE_IDENTIFIER = (
    "com.redboxgida.licensemanager"
)

datas = collect_data_files("customtkinter")

hiddenimports = [
    "cryptography",
    "cryptography.hazmat.primitives.serialization",
    "cryptography.hazmat.primitives.asymmetric.ed25519",
    "database.licensing_engine",
    "tools.license_issuer",
]

a = Analysis(
    ["tools/license_manager.py"],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "unittest",
        "database.redbox_os",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="REDBOX_License_Manager",
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
    name="REDBOX_License_Manager",
)

app = BUNDLE(
    coll,
    name="REDBOX License Manager.app",
    icon="assets/REDBOX_OS.icns",
    bundle_identifier=MANAGER_BUNDLE_IDENTIFIER,
    version=MANAGER_VERSION,
    info_plist={
        "CFBundleDisplayName": "REDBOX Lisans Yöneticisi",
        "CFBundleName": "REDBOX Lisans Yöneticisi",
        "CFBundleShortVersionString": MANAGER_VERSION,
        "CFBundleVersion": MANAGER_BUILD,
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": (
            "public.app-category.business"
        ),
    },
)

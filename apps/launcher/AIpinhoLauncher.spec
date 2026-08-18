# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).parents[1]

a = Analysis(
    [str(ROOT / "apps" / "launcher" / "ui" / "launcher_ui_main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "apps" / "launcher" / "assets" / "aipinho_launcher.ico"), "apps/launcher/assets"),
        (str(ROOT / "apps" / "launcher" / "assets" / "aipinho_launcher.png"), "apps/launcher/assets"),
        (str(ROOT / "config" / "launcher"), "config/launcher"),
    ],
    hiddenimports=["yaml"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AIpinhoLauncher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "apps" / "launcher" / "assets" / "aipinho_launcher.ico"),
)

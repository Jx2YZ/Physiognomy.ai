# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the standalone Physiognomy.ai Windows build.

Don't run PyInstaller directly — use packaging\\build.ps1, which runs this
spec and then stages config.yaml/assets/models next to the exe (they stay
outside the bundle so users can edit thresholds and swap memes).
"""
from PyInstaller.utils.hooks import collect_all

# mediapipe ships .binarypb graphs and .tflite models as package data that
# import analysis can't see; collect the whole package.
mp_datas, mp_binaries, mp_hiddenimports = collect_all("mediapipe")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=mp_binaries,
    datas=mp_datas,
    hiddenimports=mp_hiddenimports,
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
    [],
    exclude_binaries=True,
    name="Physiognomy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="packaging/icon.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Physiognomy",
)

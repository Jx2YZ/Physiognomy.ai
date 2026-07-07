# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the standalone Physiognomy.ai macOS build (.app bundle).

Must be built ON a Mac (PyInstaller cannot cross-compile). Don't run this
directly — use packaging/build_macos.sh, which runs this spec and then stages
config.yaml/assets/models next to the app so users can edit thresholds and
swap memes.
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Physiognomy",
)
app = BUNDLE(
    coll,
    name="Physiognomy.app",
    icon="packaging/icon.icns",
    bundle_identifier="ai.physiognomy.app",
    info_plist={
        # macOS shows this text in the camera-permission prompt. Required on
        # recent macOS or the app is killed the moment it opens the camera.
        "NSCameraUsageDescription": "Physiognomy.ai reads your webcam locally to detect facial expressions and hand gestures. No video ever leaves this machine.",
        "NSHighResolutionCapable": True,
    },
)

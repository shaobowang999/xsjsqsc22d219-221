# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all


datas = [
    ("main.py", "."),
    ("VERSION", "."),
    ("static", "static"),
    ("workflows", "workflows"),
]
binaries = []
# Analyze backend dependencies even though the launcher loads its source at runtime.
hiddenimports = ["main"]

for package in ("webview", "uvicorn", "fastapi", "starlette"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports


a = Analysis(
    ["desktop_app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="三千思创无线画布",
    icon="resources/desktop/sqsc.ico",
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
    name="三千思创无线画布",
)

# Add a standalone uninstaller and a manifest of packaged files.
import subprocess
from pathlib import Path
subprocess.run([
    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", str(Path(SPECPATH) / "tools" / "desktop-uninstaller" / "package-uninstaller.ps1"),
    "-AppDirectory", str(coll.name),
], check=True)

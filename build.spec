# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

pedalboard_datas = collect_data_files('pedalboard')
pedalboard_binaries = collect_dynamic_libs('pedalboard')
sounddevice_datas = collect_data_files('sounddevice')
sounddevice_binaries = collect_dynamic_libs('sounddevice')
pyside6_datas = collect_data_files('PySide6')
pyside6_binaries = collect_dynamic_libs('PySide6')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[*pedalboard_binaries, *sounddevice_binaries, *pyside6_binaries],
    datas=[
        ('assets/icon.ico', 'assets'),
        *pedalboard_datas,
        *sounddevice_datas,
        *pyside6_datas,
    ],
    hiddenimports=[
        'comtypes',
        'comtypes.client',
        'pedalboard',
        'pedalboard.pedalboard',
        'pedalboard._pedalboard',
        'pedalboard.io',
        'sounddevice',
        'numpy',
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.IcoImagePlugin',
        'queue',
        'PySide6',
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['noisereduce', 'librosa', 'scipy', 'matplotlib', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mtk-noise-canceller',
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
    icon='assets/icon.ico',
)

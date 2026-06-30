# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

pedalboard_datas = collect_data_files('pedalboard')
pedalboard_binaries = collect_dynamic_libs('pedalboard')
sounddevice_datas = collect_data_files('sounddevice')
sounddevice_binaries = collect_dynamic_libs('sounddevice')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[*pedalboard_binaries, *sounddevice_binaries],
    datas=[
        ('assets/icon.ico', 'assets'),
        *pedalboard_datas,
        *sounddevice_datas,
    ],
    hiddenimports=[
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
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['noisereduce', 'librosa', 'scipy', 'matplotlib'],
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
    uac_admin=True,
)

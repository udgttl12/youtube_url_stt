# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build spec for YouTube 화자 분리 + STT

import os
import sys
from pathlib import Path

block_cipher = None

project_root = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(project_root, 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=[
        # ffmpeg 바이너리
        (os.path.join(project_root, 'resources', 'ffmpeg', '*.exe'),
         os.path.join('resources', 'ffmpeg')),
    ],
    hiddenimports=[
        'customtkinter',
        'faster_whisper',
        'pyannote.audio',
        'torch',
        'torchaudio',
        'soundfile',
        'numpy',
        'yt_dlp',
        'pydub',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='YouTubeSTT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI 모드
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='YouTubeSTT',
)

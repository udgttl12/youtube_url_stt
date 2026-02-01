# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build spec for YouTube 화자 분리 + STT

import os
import sys
from pathlib import Path

block_cipher = None

project_root = os.path.dirname(os.path.abspath(SPEC))

# ffmpeg 바이너리가 있을 때만 번들
ffmpeg_dir = os.path.join(project_root, 'resources', 'ffmpeg')
datas_list = []
if os.path.isdir(ffmpeg_dir) and any(
    f.endswith('.exe') for f in os.listdir(ffmpeg_dir)
):
    for exe_file in os.listdir(ffmpeg_dir):
        if exe_file.endswith('.exe'):
            datas_list.append(
                (os.path.join(ffmpeg_dir, exe_file),
                 os.path.join('resources', 'ffmpeg'))
            )

# pyannote 로컬 모델 번들 (하위 디렉토리 포함)
pyannote_dir = os.path.join(project_root, 'resources', 'pyannote')
if os.path.isdir(pyannote_dir):
    for root, dirs, files in os.walk(pyannote_dir):
        rel_root = os.path.relpath(root, project_root)
        for f in files:
            datas_list.append(
                (os.path.join(root, f), rel_root)
            )

a = Analysis(
    [os.path.join(project_root, 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=datas_list,
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
        'huggingface_hub',
        'ctranslate2',
        'av',
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
    upx_exclude=['python*.dll', 'vcruntime*.dll', 'ucrtbase.dll'],
    name='YouTubeSTT',
)

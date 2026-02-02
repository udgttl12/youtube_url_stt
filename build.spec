# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build spec for YouTube 화자 분리 + STT

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

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

# pyannote 패키지 데이터 파일 (telemetry/config.yaml 등)
# venv/conda 등 환경에 관계없이 동적으로 패키지 경로를 탐색
try:
    import importlib.util
    _spec = importlib.util.find_spec('pyannote.audio')
    if _spec and _spec.origin:
        _pyannote_audio_dir = os.path.dirname(_spec.origin)
        pyannote_telemetry_yaml = os.path.join(
            _pyannote_audio_dir, 'telemetry', 'config.yaml'
        )
        if os.path.isfile(pyannote_telemetry_yaml):
            datas_list.append(
                (pyannote_telemetry_yaml, os.path.join('pyannote', 'audio', 'telemetry'))
            )
except Exception:
    pass

# faster_whisper VAD 모델 (silero_vad_v6.onnx) 번들
datas_list += collect_data_files('faster_whisper')

a = Analysis(
    [os.path.join(project_root, 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        'customtkinter',
        'faster_whisper',
        'torch',
        'torchaudio',
        'soundfile',
        'numpy',
        'yt_dlp',
        'pydub',
        'huggingface_hub',
        'ctranslate2',
        'av',
    ] + collect_submodules('pyannote.audio'),
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['python*.dll', 'vcruntime*.dll', 'ucrtbase.dll'],
    name='YouTubeSTT',
)

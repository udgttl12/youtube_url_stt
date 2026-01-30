"""경로 관리 유틸리티."""

import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """프로젝트 루트 또는 PyInstaller 번들 기준 경로 반환."""
    if getattr(sys, "frozen", False):
        # PyInstaller --onedir 모드
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def get_app_data_dir() -> Path:
    """사용자별 앱 데이터 디렉토리 반환 (~/.youtube_stt/)."""
    app_dir = Path.home() / ".youtube_stt"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_models_dir() -> Path:
    """모델 캐시 디렉토리 반환."""
    models_dir = get_app_data_dir() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def get_temp_dir() -> Path:
    """임시 파일 디렉토리 반환."""
    temp_dir = get_app_data_dir() / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_output_dir() -> Path:
    """기본 출력 디렉토리 반환."""
    output_dir = get_app_data_dir() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_ffmpeg_path() -> str:
    """ffmpeg 실행 파일 경로 반환.

    1. resources/ffmpeg/ 내장 바이너리
    2. 시스템 PATH의 ffmpeg
    """
    base = get_base_dir()
    bundled = base / "resources" / "ffmpeg" / "ffmpeg.exe"
    if bundled.exists():
        return str(bundled)

    # 시스템 PATH에서 찾기
    import shutil
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    return "ffmpeg"  # 마지막 시도 - pydub이 자체 탐색


def get_ffprobe_path() -> str:
    """ffprobe 실행 파일 경로 반환."""
    base = get_base_dir()
    bundled = base / "resources" / "ffmpeg" / "ffprobe.exe"
    if bundled.exists():
        return str(bundled)

    import shutil
    system_ffprobe = shutil.which("ffprobe")
    if system_ffprobe:
        return system_ffprobe

    return "ffprobe"


def get_config_path() -> Path:
    """설정 파일 경로 반환."""
    return get_app_data_dir() / "config.json"


def cleanup_temp():
    """임시 디렉토리 내 파일 정리."""
    temp_dir = get_temp_dir()
    for f in temp_dir.iterdir():
        try:
            if f.is_file():
                f.unlink()
        except OSError:
            pass

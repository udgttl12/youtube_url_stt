"""경로 관리 유틸리티."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


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


def get_ffmpeg_dir() -> Path:
    """사용자 다운로드 ffmpeg 디렉토리 반환 (~/.youtube_stt/ffmpeg/)."""
    ffmpeg_dir = get_app_data_dir() / "ffmpeg"
    ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    return ffmpeg_dir


def get_ffmpeg_path() -> str:
    """ffmpeg 실행 파일 경로 반환.

    1. resources/ffmpeg/ 내장 바이너리 (PyInstaller 번들)
    2. ~/.youtube_stt/ffmpeg/ 사용자 다운로드
    3. 시스템 PATH의 ffmpeg
    """
    base = get_base_dir()
    bundled = base / "resources" / "ffmpeg" / "ffmpeg.exe"
    if bundled.exists():
        return str(bundled)

    # 사용자 다운로드 경로
    user_ffmpeg = get_app_data_dir() / "ffmpeg" / "ffmpeg.exe"
    if user_ffmpeg.exists():
        return str(user_ffmpeg)

    # 시스템 PATH에서 찾기
    import shutil
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    return "ffmpeg"  # 마지막 시도 - pydub이 자체 탐색


def get_ffprobe_path() -> str:
    """ffprobe 실행 파일 경로 반환.

    1. resources/ffmpeg/ 내장 바이너리 (PyInstaller 번들)
    2. ~/.youtube_stt/ffmpeg/ 사용자 다운로드
    3. 시스템 PATH의 ffprobe
    """
    base = get_base_dir()
    bundled = base / "resources" / "ffmpeg" / "ffprobe.exe"
    if bundled.exists():
        return str(bundled)

    # 사용자 다운로드 경로
    user_ffprobe = get_app_data_dir() / "ffmpeg" / "ffprobe.exe"
    if user_ffprobe.exists():
        return str(user_ffprobe)

    import shutil
    system_ffprobe = shutil.which("ffprobe")
    if system_ffprobe:
        return system_ffprobe

    return "ffprobe"


def get_pyannote_dir() -> Path:
    """로컬 번들 pyannote 모델 디렉토리 반환.

    PyInstaller 번들 환경과 개발 환경 모두 지원.
    """
    return get_base_dir() / "resources" / "pyannote"


def get_pyannote_config_path() -> Optional[Path]:
    """pyannote config.yaml 경로 반환. 모델 파일이 없으면 None.

    config.yaml이 없지만 모델 .bin 파일이 존재하면 자동 생성.
    """
    pyannote_dir = get_pyannote_dir()
    if not pyannote_dir.is_dir():
        return None

    # 필수 모델 파일 확인
    seg_bin = pyannote_dir / "pyannote_model_segmentation-3.0.bin"
    emb_bin = pyannote_dir / "pyannote_model_wespeaker-voxceleb-resnet34-LM.bin"

    if not seg_bin.exists() or not emb_bin.exists():
        return None

    config_path = pyannote_dir / "config.yaml"
    if not config_path.exists():
        _generate_pyannote_config(config_path)

    return config_path


def _generate_pyannote_config(config_path: Path) -> None:
    """pyannote speaker-diarization-3.1 config.yaml 및 PLDA 더미 파일 자동 생성.

    모델 경로는 config.yaml 기준 상대경로로 지정.
    AgglomerativeClustering 사용 시 PLDA는 로드되지만 실제 사용되지 않으므로
    유효한 형식의 더미 파일을 생성한다.
    """
    config_content = """\
version: 3.1.0

pipeline:
  name: pyannote.audio.pipelines.SpeakerDiarization
  params:
    clustering: AgglomerativeClustering
    embedding: pyannote_model_wespeaker-voxceleb-resnet34-LM.bin
    embedding_batch_size: 32
    embedding_exclude_overlap: true
    plda: plda
    segmentation: pyannote_model_segmentation-3.0.bin
    segmentation_batch_size: 32

params:
  clustering:
    method: centroid
    min_cluster_size: 12
    threshold: 0.7045654963945799
  segmentation:
    min_duration_off: 0.0
"""
    try:
        config_path.write_text(config_content, encoding="utf-8")
        logger.info(f"pyannote config.yaml 생성: {config_path}")
    except OSError as e:
        logger.error(f"pyannote config.yaml 생성 실패: {e}")

    # PLDA 더미 파일 생성 (AgglomerativeClustering에서는 미사용)
    _ensure_plda_dummy(config_path.parent / "plda")


def _ensure_plda_dummy(plda_dir: Path) -> None:
    """PLDA 더미 npz 파일이 없으면 생성."""
    transform_path = plda_dir / "xvec_transform.npz"
    plda_path = plda_dir / "plda.npz"
    if transform_path.exists() and plda_path.exists():
        return

    try:
        import numpy as np

        plda_dir.mkdir(parents=True, exist_ok=True)
        dim, lda_dim = 256, 128

        np.savez(
            transform_path,
            mean1=np.zeros(dim),
            mean2=np.zeros(lda_dim),
            lda=np.eye(lda_dim, dim),
        )
        np.savez(
            plda_path,
            mu=np.zeros(lda_dim),
            tr=np.eye(lda_dim),
            psi=np.ones(lda_dim),
        )
        logger.info(f"PLDA 더미 파일 생성: {plda_dir}")
    except Exception as e:
        logger.error(f"PLDA 더미 파일 생성 실패: {e}")


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

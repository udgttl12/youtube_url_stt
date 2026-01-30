"""외부 의존성 다운로드 및 상태 점검 모듈."""

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

from src.utils.exceptions import DependencySetupError
from src.utils.paths import get_app_data_dir, get_ffmpeg_path, get_ffprobe_path

logger = logging.getLogger(__name__)

# ffmpeg 다운로드 URL (Windows essentials build)
FFMPEG_URL_PRIMARY = (
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
)
FFMPEG_URL_FALLBACK = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
    "latest/ffmpeg-master-latest-win64-gpl.zip"
)

# 콜백 타입: (progress_ratio: float 0~1, message: str)
ProgressCallback = Callable[[float, str], None]


def _noop_callback(ratio: float, message: str) -> None:
    pass


# ─── ffmpeg 관련 ──────────────────────────────────────────────

def get_ffmpeg_dir() -> Path:
    """사용자 다운로드 ffmpeg 디렉토리."""
    ffmpeg_dir = get_app_data_dir() / "ffmpeg"
    ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    return ffmpeg_dir


def is_ffmpeg_available() -> bool:
    """ffmpeg가 실행 가능한 상태인지 확인."""
    ffmpeg = get_ffmpeg_path()
    if ffmpeg == "ffmpeg":
        # 폴백 값이면 실제 존재 여부 확인
        return shutil.which("ffmpeg") is not None
    return Path(ffmpeg).exists()


def get_ffmpeg_version() -> Optional[str]:
    """설치된 ffmpeg 버전 문자열 반환. 실패 시 None."""
    try:
        ffmpeg = get_ffmpeg_path()
        result = subprocess.run(
            [ffmpeg, "-version"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if result.returncode == 0:
            # 첫 줄에서 버전 추출: "ffmpeg version 7.0-essentials ..."
            first_line = result.stdout.strip().split("\n")[0]
            parts = first_line.split()
            if len(parts) >= 3:
                return parts[2]
        return None
    except Exception:
        return None


def download_ffmpeg(progress_callback: ProgressCallback = _noop_callback) -> Path:
    """ffmpeg를 다운로드하여 ~/.youtube_stt/ffmpeg/에 설치.

    Returns:
        ffmpeg.exe 경로
    Raises:
        DependencySetupError: 다운로드 또는 설치 실패 시
    """
    dest_dir = get_ffmpeg_dir()
    ffmpeg_exe = dest_dir / "ffmpeg.exe"
    ffprobe_exe = dest_dir / "ffprobe.exe"

    # 이미 존재하면 스킵
    if ffmpeg_exe.exists() and ffprobe_exe.exists():
        progress_callback(1.0, "ffmpeg가 이미 설치되어 있습니다.")
        return ffmpeg_exe

    progress_callback(0.0, "ffmpeg 다운로드 준비 중...")

    # 다운로드 시도 (primary → fallback)
    zip_path = None
    for i, url in enumerate([FFMPEG_URL_PRIMARY, FFMPEG_URL_FALLBACK]):
        try:
            progress_callback(0.05, f"ffmpeg 다운로드 중... (소스 {i + 1})")
            zip_path = _download_file(url, dest_dir, progress_callback)
            break
        except Exception as e:
            logger.warning(f"ffmpeg 다운로드 실패 (소스 {i + 1}): {e}")
            if i == 1:
                raise DependencySetupError(
                    "ffmpeg 다운로드에 실패했습니다. "
                    "네트워크 연결을 확인하거나 수동으로 설치해주세요.\n"
                    "수동 설치: https://www.gyan.dev/ffmpeg/builds/"
                ) from e

    if not zip_path:
        raise DependencySetupError("ffmpeg 다운로드 파일을 찾을 수 없습니다.")

    # zip 압축 해제
    try:
        progress_callback(0.8, "ffmpeg 압축 해제 중...")
        _extract_ffmpeg_from_zip(zip_path, dest_dir)
    except Exception as e:
        # 불완전 파일 정리
        for f in [ffmpeg_exe, ffprobe_exe]:
            if f.exists():
                f.unlink()
        raise DependencySetupError(f"ffmpeg 압축 해제 실패: {e}") from e
    finally:
        # zip 파일 정리
        if zip_path and zip_path.exists():
            try:
                zip_path.unlink()
            except OSError:
                pass

    if not ffmpeg_exe.exists():
        raise DependencySetupError(
            "ffmpeg 설치 후 실행 파일을 찾을 수 없습니다."
        )

    progress_callback(1.0, "ffmpeg 설치 완료!")
    logger.info(f"ffmpeg 설치됨: {ffmpeg_exe}")
    return ffmpeg_exe


def _download_file(
    url: str,
    dest_dir: Path,
    progress_callback: ProgressCallback,
) -> Path:
    """URL에서 파일을 다운로드하여 dest_dir에 저장."""
    request = Request(url, headers={"User-Agent": "youtube-stt/1.0"})
    response = urlopen(request, timeout=60)

    total_size = int(response.headers.get("Content-Length", 0))
    dest_path = dest_dir / "ffmpeg_download.zip"

    downloaded = 0
    chunk_size = 1024 * 256  # 256KB

    with open(dest_path, "wb") as f:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)

            if total_size > 0:
                ratio = 0.05 + (downloaded / total_size) * 0.75  # 5%~80%
                size_mb = downloaded / (1024 * 1024)
                total_mb = total_size / (1024 * 1024)
                progress_callback(
                    ratio,
                    f"ffmpeg 다운로드 중... {size_mb:.1f}/{total_mb:.1f} MB",
                )

    return dest_path


def _extract_ffmpeg_from_zip(zip_path: Path, dest_dir: Path) -> None:
    """zip에서 ffmpeg.exe, ffprobe.exe를 추출."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        # zip 내부에서 ffmpeg.exe, ffprobe.exe 찾기
        ffmpeg_found = False
        ffprobe_found = False

        for info in zf.infolist():
            name_lower = info.filename.lower()
            basename = Path(info.filename).name.lower()

            if basename == "ffmpeg.exe":
                _extract_single(zf, info, dest_dir / "ffmpeg.exe")
                ffmpeg_found = True
            elif basename == "ffprobe.exe":
                _extract_single(zf, info, dest_dir / "ffprobe.exe")
                ffprobe_found = True

            if ffmpeg_found and ffprobe_found:
                break

        if not ffmpeg_found:
            raise DependencySetupError(
                "zip 파일에서 ffmpeg.exe를 찾을 수 없습니다."
            )


def _extract_single(zf: zipfile.ZipFile, info: zipfile.ZipInfo, dest: Path) -> None:
    """zip에서 단일 파일을 지정된 경로로 추출."""
    with zf.open(info) as src, open(dest, "wb") as dst:
        shutil.copyfileobj(src, dst)


# ─── 삭제 ─────────────────────────────────────────────────────

def delete_ffmpeg() -> bool:
    """~/.youtube_stt/ffmpeg/ 내 파일 삭제."""
    ffmpeg_dir = get_ffmpeg_dir()
    for f in ["ffmpeg.exe", "ffprobe.exe"]:
        fp = ffmpeg_dir / f
        if fp.exists():
            fp.unlink()
    return True


def delete_whisper_model(model_name: str = "large-v3") -> bool:
    """HuggingFace 캐시에서 faster-whisper 모델 삭제."""
    from huggingface_hub import scan_cache_dir
    cache = scan_cache_dir()
    repo_name = f"Systran/faster-whisper-{model_name}"
    for repo in cache.repos:
        if repo.repo_id == repo_name:
            delete_strategy = cache.delete_revisions(
                *[rev.commit_hash for rev in repo.revisions]
            )
            delete_strategy.execute()
            return True
    return False


def delete_diarize_model() -> bool:
    """HuggingFace 캐시에서 pyannote 모델 삭제."""
    from huggingface_hub import scan_cache_dir
    cache = scan_cache_dir()
    targets = {"pyannote/speaker-diarization-3.1", "pyannote/segmentation-3.0"}
    for repo in cache.repos:
        if repo.repo_id in targets:
            delete_strategy = cache.delete_revisions(
                *[rev.commit_hash for rev in repo.revisions]
            )
            delete_strategy.execute()
    return True


# ─── 용량 계산 ─────────────────────────────────────────────────

def get_ffmpeg_size() -> int:
    """ffmpeg 설치 용량 (bytes). 미설치 시 0."""
    ffmpeg_dir = get_ffmpeg_dir()
    total = 0
    for f in ffmpeg_dir.iterdir():
        if f.is_file():
            total += f.stat().st_size
    return total


def get_whisper_model_size(model_name: str = "large-v3") -> int:
    """Whisper 모델 캐시 용량 (bytes). 미설치 시 0."""
    try:
        from huggingface_hub import scan_cache_dir
        cache = scan_cache_dir()
        repo_name = f"Systran/faster-whisper-{model_name}"
        for repo in cache.repos:
            if repo.repo_id == repo_name:
                return repo.size_on_disk
    except Exception:
        pass
    return 0


def get_diarize_model_size() -> int:
    """pyannote 모델 캐시 용량 (bytes). 미설치 시 0."""
    try:
        from huggingface_hub import scan_cache_dir
        cache = scan_cache_dir()
        targets = {"pyannote/speaker-diarization-3.1", "pyannote/segmentation-3.0"}
        total = 0
        for repo in cache.repos:
            if repo.repo_id in targets:
                total += repo.size_on_disk
        return total
    except Exception:
        return 0


def format_size(size_bytes: int) -> str:
    """바이트를 사람이 읽기 쉬운 형식으로 변환."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"


# ─── 모델 관련 ────────────────────────────────────────────────

def is_whisper_model_cached(model_name: str = "large-v3") -> bool:
    """faster-whisper 모델이 캐시되어 있는지 확인."""
    try:
        from huggingface_hub import scan_cache_dir
        cache_info = scan_cache_dir()
        repo_name = f"Systran/faster-whisper-{model_name}"
        for repo in cache_info.repos:
            if repo.repo_id == repo_name:
                return True
        return False
    except Exception:
        return False


def is_diarize_model_cached() -> bool:
    """pyannote 화자 분리 모델이 캐시되어 있는지 확인."""
    try:
        from huggingface_hub import scan_cache_dir
        cache_info = scan_cache_dir()
        target_repos = {
            "pyannote/speaker-diarization-3.1",
            "pyannote/segmentation-3.0",
        }
        found = set()
        for repo in cache_info.repos:
            if repo.repo_id in target_repos:
                found.add(repo.repo_id)
        return len(found) >= 1  # 최소 메인 파이프라인만 있으면 OK
    except Exception:
        return False


def download_whisper_model(
    model_name: str = "large-v3",
    progress_callback: ProgressCallback = _noop_callback,
) -> bool:
    """faster-whisper 모델 사전 다운로드.

    Returns:
        성공 여부
    """
    if is_whisper_model_cached(model_name):
        progress_callback(1.0, f"Whisper {model_name} 모델이 이미 캐시되어 있습니다.")
        return True

    try:
        progress_callback(0.1, f"Whisper {model_name} 모델 다운로드 중... (수 GB, 시간 소요)")
        from faster_whisper import WhisperModel
        # CPU/int8로 로드하여 다운로드 트리거 (메모리 절약)
        _model = WhisperModel(model_name, device="cpu", compute_type="int8")
        del _model
        progress_callback(1.0, f"Whisper {model_name} 모델 다운로드 완료!")
        return True
    except Exception as e:
        logger.error(f"Whisper 모델 다운로드 실패: {e}")
        progress_callback(0.0, f"Whisper 모델 다운로드 실패: {e}")
        return False


def download_diarize_model(
    hf_token: str,
    progress_callback: ProgressCallback = _noop_callback,
) -> bool:
    """pyannote 화자 분리 모델 사전 다운로드.

    Returns:
        성공 여부
    """
    if not hf_token:
        progress_callback(0.0, "HuggingFace 토큰이 필요합니다.")
        return False

    if is_diarize_model_cached():
        progress_callback(1.0, "화자 분리 모델이 이미 캐시되어 있습니다.")
        return True

    try:
        progress_callback(0.1, "화자 분리 모델 다운로드 중...")
        from pyannote.audio import Pipeline as PyannotePipeline
        _pipeline = PyannotePipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=hf_token,
        )
        del _pipeline
        progress_callback(1.0, "화자 분리 모델 다운로드 완료!")
        return True
    except Exception as e:
        logger.error(f"화자 분리 모델 다운로드 실패: {e}")
        progress_callback(0.0, f"화자 분리 모델 다운로드 실패: {e}")
        return False


# ─── 상태 점검 ────────────────────────────────────────────────

@dataclass
class DependencyStatus:
    """외부 의존성 상태."""
    ffmpeg_available: bool = False
    ffmpeg_path: str = ""
    ffmpeg_version: Optional[str] = None
    hf_token_available: bool = False
    whisper_model_cached: bool = False
    diarize_model_cached: bool = False

    @classmethod
    def check_all(cls, hf_token: str = "") -> "DependencyStatus":
        """전체 의존성 상태를 점검."""
        status = cls()

        # ffmpeg
        status.ffmpeg_available = is_ffmpeg_available()
        if status.ffmpeg_available:
            status.ffmpeg_path = get_ffmpeg_path()
            status.ffmpeg_version = get_ffmpeg_version()

        # HF 토큰
        status.hf_token_available = bool(hf_token and hf_token.strip())

        # 모델 캐시
        status.whisper_model_cached = is_whisper_model_cached()
        status.diarize_model_cached = is_diarize_model_cached()

        return status

    @property
    def needs_setup(self) -> bool:
        """필수 의존성(ffmpeg)이 없으면 True."""
        return not self.ffmpeg_available


# ─── CLI 셋업 ────────────────────────────────────────────────

def run_setup(
    hf_token: str = "",
    progress_callback: ProgressCallback = _noop_callback,
) -> dict:
    """전체 의존성 셋업 실행 (CLI --setup 용).

    Returns:
        각 항목별 결과 dict
    """
    results = {}

    # 1. ffmpeg
    try:
        download_ffmpeg(progress_callback)
        results["ffmpeg"] = "OK"
    except DependencySetupError as e:
        results["ffmpeg"] = f"FAIL: {e}"

    # 2. Whisper 모델
    try:
        ok = download_whisper_model(progress_callback=progress_callback)
        results["whisper"] = "OK" if ok else "FAIL"
    except Exception as e:
        results["whisper"] = f"FAIL: {e}"

    # 3. 화자 분리 모델
    if hf_token:
        try:
            ok = download_diarize_model(hf_token, progress_callback)
            results["diarize"] = "OK" if ok else "FAIL"
        except Exception as e:
            results["diarize"] = f"FAIL: {e}"
    else:
        results["diarize"] = "SKIP (HF 토큰 없음)"

    return results

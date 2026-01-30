"""YouTube 오디오 다운로드 모듈."""

import logging
import re
import time
from pathlib import Path
from typing import Callable, Optional

import yt_dlp

from src.utils.exceptions import DownloadError
from src.utils.paths import get_temp_dir, get_ffmpeg_path

logger = logging.getLogger(__name__)

# YouTube URL 패턴
YOUTUBE_URL_PATTERN = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)"
    r"[\w\-]{11}"
)


def validate_url(url: str) -> bool:
    """YouTube URL 유효성 검사."""
    return bool(YOUTUBE_URL_PATTERN.match(url.strip()))


class YouTubeDownloader:
    """YouTube 영상에서 오디오를 다운로드."""

    MAX_RETRIES = 3
    RETRY_DELAY = 2  # 초

    def __init__(self, progress_callback: Optional[Callable[[float, str], None]] = None):
        """
        Args:
            progress_callback: (progress_ratio, status_text) 콜백
        """
        self._progress_callback = progress_callback

    def download(self, url: str, output_dir: Optional[Path] = None) -> Path:
        """YouTube URL에서 오디오를 WAV로 다운로드.

        Args:
            url: YouTube URL
            output_dir: 저장 디렉토리 (기본: temp)

        Returns:
            다운로드된 WAV 파일 경로

        Raises:
            DownloadError: 다운로드 실패
        """
        if not validate_url(url):
            raise DownloadError(f"유효하지 않은 YouTube URL: {url}")

        output_dir = output_dir or get_temp_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "audio_raw"

        ffmpeg_path = get_ffmpeg_path()

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(output_path),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }],
            "ffmpeg_location": str(Path(ffmpeg_path).parent),
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [self._ydl_progress_hook],
        }

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"다운로드 시도 {attempt}/{self.MAX_RETRIES}: {url}")
                self._report_progress(0.0, f"다운로드 시도 {attempt}/{self.MAX_RETRIES}...")

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "unknown")
                    duration = info.get("duration", 0)
                    logger.info(f"영상 정보: '{title}' ({duration}초)")

                wav_path = output_path.with_suffix(".wav")
                if wav_path.exists():
                    logger.info(f"다운로드 완료: {wav_path}")
                    self._report_progress(1.0, "다운로드 완료")
                    return wav_path

                raise DownloadError("WAV 파일이 생성되지 않음")

            except DownloadError:
                raise
            except Exception as e:
                last_error = e
                logger.warning(f"다운로드 실패 (시도 {attempt}): {e}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)

        raise DownloadError(
            f"다운로드 {self.MAX_RETRIES}회 시도 실패: {last_error}"
        )

    def get_video_info(self, url: str) -> dict:
        """영상 메타데이터만 조회 (다운로드하지 않음)."""
        try:
            ydl_opts = {"quiet": True, "no_warnings": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title", ""),
                    "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", ""),
                    "thumbnail": info.get("thumbnail", ""),
                }
        except Exception as e:
            logger.warning(f"영상 정보 조회 실패: {e}")
            return {}

    def _ydl_progress_hook(self, d: dict):
        """yt-dlp 진행률 콜백."""
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                ratio = downloaded / total
                self._report_progress(ratio * 0.9, f"다운로드 중... {ratio*100:.0f}%")
        elif d["status"] == "finished":
            self._report_progress(0.9, "변환 중...")

    def _report_progress(self, ratio: float, text: str):
        if self._progress_callback:
            self._progress_callback(ratio, text)

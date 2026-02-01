"""오디오 전처리 모듈 - 16kHz mono WAV 변환, 음량 정규화, 클리핑 방지."""

import logging
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import soundfile as sf

from src.utils.exceptions import CancelledError, PreprocessError
from src.utils.paths import get_temp_dir

logger = logging.getLogger(__name__)

TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1  # mono
TARGET_DB = -20.0  # 목표 RMS dB
CLIP_THRESHOLD = 0.99


class AudioPreprocessor:
    """오디오를 STT에 최적화된 형태로 전처리."""

    def __init__(
        self,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ):
        self._progress_callback = progress_callback
        self._cancel_check = cancel_check

    def process(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """오디오 파일을 전처리.

        Args:
            input_path: 입력 오디오 파일
            output_path: 출력 파일 경로 (기본: temp/preprocessed.wav)

        Returns:
            전처리된 WAV 파일 경로

        Raises:
            PreprocessError: 전처리 실패
        """
        if not input_path.exists():
            raise PreprocessError(f"입력 파일이 존재하지 않음: {input_path}")

        output_path = output_path or (get_temp_dir() / "preprocessed.wav")

        try:
            self._report_progress(0.0, "오디오 로딩 중...")
            data, sr = sf.read(str(input_path), dtype="float32")
            logger.info(f"원본 오디오: {sr}Hz, shape={data.shape}")
            self._check_cancelled()

            # 1. 모노 변환
            self._report_progress(0.2, "모노 변환 중...")
            data = self._to_mono(data)
            self._check_cancelled()

            # 2. 리샘플링
            self._report_progress(0.4, "리샘플링 중...")
            data = self._resample(data, sr, TARGET_SAMPLE_RATE)
            self._check_cancelled()

            # 3. 음량 정규화
            self._report_progress(0.6, "음량 정규화 중...")
            data = self._normalize_volume(data)
            self._check_cancelled()

            # 4. 클리핑 방지
            self._report_progress(0.8, "클리핑 방지 처리 중...")
            data = self._prevent_clipping(data)
            self._check_cancelled()

            # 5. 저장
            self._report_progress(0.9, "저장 중...")
            sf.write(str(output_path), data, TARGET_SAMPLE_RATE, subtype="PCM_16")

            duration = len(data) / TARGET_SAMPLE_RATE
            logger.info(f"전처리 완료: {output_path} ({duration:.1f}초)")
            self._report_progress(1.0, "전처리 완료")

            return output_path

        except CancelledError:
            raise
        except PreprocessError:
            raise
        except Exception as e:
            raise PreprocessError(f"오디오 전처리 실패: {e}")

    def _to_mono(self, data: np.ndarray) -> np.ndarray:
        """다채널 오디오를 모노로 변환."""
        if data.ndim == 1:
            return data
        # 다채널 → 평균으로 모노 변환
        return data.mean(axis=1).astype(np.float32)

    def _resample(self, data: np.ndarray, src_rate: int, target_rate: int) -> np.ndarray:
        """샘플링 레이트 변환."""
        if src_rate == target_rate:
            return data

        # numpy 기반 선형 보간 리샘플링
        duration = len(data) / src_rate
        target_length = int(duration * target_rate)
        x_old = np.linspace(0, 1, len(data))
        x_new = np.linspace(0, 1, target_length)
        resampled = np.interp(x_new, x_old, data).astype(np.float32)

        logger.info(f"리샘플링: {src_rate}Hz → {target_rate}Hz")
        return resampled

    def _normalize_volume(self, data: np.ndarray) -> np.ndarray:
        """RMS 기반 음량 정규화."""
        rms = np.sqrt(np.mean(data ** 2))
        if rms < 1e-10:
            logger.warning("오디오가 거의 무음")
            return data

        current_db = 20 * np.log10(rms)
        gain_db = TARGET_DB - current_db
        gain = 10 ** (gain_db / 20)
        normalized = (data * gain).astype(np.float32)

        logger.info(f"음량 정규화: {current_db:.1f}dB → {TARGET_DB:.1f}dB (gain: {gain_db:+.1f}dB)")
        return normalized

    def _prevent_clipping(self, data: np.ndarray) -> np.ndarray:
        """클리핑 방지 - 피크가 임계값 초과 시 리미팅."""
        peak = np.max(np.abs(data))
        if peak > CLIP_THRESHOLD:
            scale = CLIP_THRESHOLD / peak
            data = (data * scale).astype(np.float32)
            logger.info(f"클리핑 방지: 피크 {peak:.4f} → {CLIP_THRESHOLD}")
        return data

    def _check_cancelled(self):
        if self._cancel_check and self._cancel_check():
            raise CancelledError()

    def _report_progress(self, ratio: float, text: str):
        if self._progress_callback:
            self._progress_callback(ratio, text)

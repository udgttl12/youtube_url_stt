"""파이프라인 오케스트레이터 - 전체 처리 흐름 관리."""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from src.core.downloader import YouTubeDownloader
from src.core.preprocessor import AudioPreprocessor
from src.core.transcriber import Transcriber, TranscriptResult
from src.core.diarizer import SpeakerDiarizer, DiarizeResult
from src.core.merger import ResultMerger, MergedResult
from src.utils.device import DeviceManager, DeviceConfig
from src.utils.config import AppConfig
from src.utils.exceptions import YouTubeSTTError, DiarizeError
from src.utils.paths import cleanup_temp, get_pyannote_config_path

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """파이프라인 단계."""
    INIT = "초기화"
    DOWNLOAD = "다운로드"
    PREPROCESS = "전처리"
    DIARIZE = "화자 분리"
    TRANSCRIBE = "STT"
    MERGE = "병합"
    OUTPUT = "출력"
    DONE = "완료"
    ERROR = "오류"


@dataclass
class PipelineConfig:
    """파이프라인 설정."""
    url: str
    language: str = "auto"
    num_speakers: Optional[int] = None
    output_format: str = "txt"
    output_dir: str = ""
    enable_diarization: bool = True
    use_vad: bool = True
    high_accuracy: bool = False
    hf_token: str = ""


class Pipeline:
    """전체 처리 파이프라인 오케스트레이터.

    YouTube URL → 다운로드 → 전처리 → 화자 분리 → STT → 병합 → 출력
    """

    def __init__(
        self,
        config: PipelineConfig,
        stage_callback: Optional[Callable[[PipelineStage, float, str], None]] = None,
        device_config: Optional[DeviceConfig] = None,
    ):
        """
        Args:
            config: 파이프라인 설정
            stage_callback: (stage, progress, message) 콜백
            device_config: 디바이스 설정 (None이면 자동 감지)
        """
        self._config = config
        self._stage_callback = stage_callback
        self._device_config = device_config or DeviceManager.detect()
        self._cancelled = False

    def cancel(self):
        """파이프라인 취소."""
        self._cancelled = True
        logger.info("파이프라인 취소 요청됨")

    def run(self) -> MergedResult:
        """전체 파이프라인 실행.

        Returns:
            MergedResult: 최종 병합 결과

        Raises:
            YouTubeSTTError: 처리 실패
        """
        start_time = time.time()

        try:
            # 1. 초기화
            self._notify(PipelineStage.INIT, 0.0, "파이프라인 초기화...")
            self._check_cancelled()

            # 2. 다운로드
            self._notify(PipelineStage.DOWNLOAD, 0.0, "다운로드 시작...")
            downloader = YouTubeDownloader(
                progress_callback=lambda p, t: self._notify(PipelineStage.DOWNLOAD, p, t)
            )
            raw_audio = downloader.download(self._config.url)
            self._check_cancelled()

            # 3. 전처리
            self._notify(PipelineStage.PREPROCESS, 0.0, "오디오 전처리 시작...")
            preprocessor = AudioPreprocessor(
                progress_callback=lambda p, t: self._notify(PipelineStage.PREPROCESS, p, t)
            )
            processed_audio = preprocessor.process(raw_audio)
            self._check_cancelled()

            # 4. 화자 분리 (선택적)
            diarize_result: Optional[DiarizeResult] = None
            local_model = get_pyannote_config_path()
            has_local_model = local_model is not None and local_model.exists()
            can_diarize = self._config.enable_diarization and (
                self._config.hf_token or has_local_model
            )
            if can_diarize:
                try:
                    self._notify(PipelineStage.DIARIZE, 0.0, "화자 분리 시작...")
                    diarizer = SpeakerDiarizer(
                        hf_token=self._config.hf_token,
                        device=self._device_config.device,
                        progress_callback=lambda p, t: self._notify(PipelineStage.DIARIZE, p, t),
                    )
                    diarize_result = diarizer.diarize(
                        processed_audio,
                        num_speakers=self._config.num_speakers,
                    )
                except DiarizeError as e:
                    logger.warning(f"화자 분리 실패, 단일 화자로 진행: {e}")
                    self._notify(
                        PipelineStage.DIARIZE, 1.0,
                        "화자 분리 실패 - 단일 화자로 처리"
                    )
            elif self._config.enable_diarization:
                logger.info("HuggingFace 토큰 없고 로컬 모델도 없음, 화자 분리 건너뜀")
                self._notify(
                    PipelineStage.DIARIZE, 1.0,
                    "HF 토큰/로컬 모델 없음 - 화자 분리 건너뜀"
                )
            else:
                self._notify(PipelineStage.DIARIZE, 1.0, "화자 분리 건너뜀")

            self._check_cancelled()

            # 5. STT
            self._notify(PipelineStage.TRANSCRIBE, 0.0, "STT 시작...")
            transcriber = Transcriber(
                device_config=self._device_config,
                progress_callback=lambda p, t: self._notify(PipelineStage.TRANSCRIBE, p, t),
            )

            language = self._config.language if self._config.language != "auto" else None
            if self._config.use_vad:
                transcript_result = transcriber.transcribe_with_vad(
                    processed_audio, language=language
                )
            else:
                transcript_result = transcriber.transcribe_full(
                    processed_audio, language=language
                )
            self._check_cancelled()

            # 6. 병합
            self._notify(PipelineStage.MERGE, 0.0, "결과 병합 중...")
            merged = ResultMerger.merge(transcript_result, diarize_result)
            self._notify(PipelineStage.MERGE, 1.0, "병합 완료")

            # 완료
            elapsed = time.time() - start_time
            logger.info(f"파이프라인 완료: {elapsed:.1f}초")
            self._notify(
                PipelineStage.DONE, 1.0,
                f"처리 완료 ({elapsed:.0f}초 소요)"
            )

            # 임시 파일 정리
            cleanup_temp()

            return merged

        except YouTubeSTTError:
            raise
        except Exception as e:
            self._notify(PipelineStage.ERROR, 0.0, f"오류: {e}")
            raise YouTubeSTTError(f"파이프라인 실행 실패: {e}")

    def _check_cancelled(self):
        if self._cancelled:
            raise YouTubeSTTError("사용자에 의해 취소됨")

    def _notify(self, stage: PipelineStage, progress: float, message: str):
        logger.debug(f"[{stage.value}] {progress:.0%} - {message}")
        if self._stage_callback:
            self._stage_callback(stage, progress, message)

"""STT(Speech-to-Text) 모듈 - faster-whisper 기반."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from src.utils.device import DeviceConfig
from src.utils.exceptions import TranscribeError, ModelLoadError

logger = logging.getLogger(__name__)


@dataclass
class WordSegment:
    """단어 단위 세그먼트."""
    word: str
    start: float
    end: float
    probability: float = 0.0


@dataclass
class TranscriptSegment:
    """문장 단위 세그먼트."""
    text: str
    start: float
    end: float
    words: List[WordSegment] = field(default_factory=list)


@dataclass
class TranscriptResult:
    """전사 결과."""
    segments: List[TranscriptSegment]
    language: str = ""
    language_probability: float = 0.0
    duration: float = 0.0


class Transcriber:
    """faster-whisper 기반 STT 엔진."""

    def __init__(
        self,
        device_config: DeviceConfig,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ):
        self._device_config = device_config
        self._progress_callback = progress_callback
        self._model = None

    def load_model(self):
        """Whisper 모델 로드."""
        try:
            from faster_whisper import WhisperModel

            model_size = self._device_config.whisper_model
            device = self._device_config.device
            compute_type = self._device_config.compute_type

            logger.info(
                f"모델 로드: {model_size} (device={device}, compute={compute_type})"
            )
            self._report_progress(0.0, f"Whisper {model_size} 모델 로드 중...")

            self._model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
            )
            logger.info("모델 로드 완료")
            self._report_progress(1.0, "모델 로드 완료")

        except Exception as e:
            raise ModelLoadError(f"Whisper 모델 로드 실패: {e}")

    def transcribe_full(
        self,
        audio_path: Path,
        language: Optional[str] = None,
    ) -> TranscriptResult:
        """전체 오디오를 한 번에 전사.

        Args:
            audio_path: 전처리된 WAV 파일
            language: 언어 코드 (None이면 자동 감지)

        Returns:
            TranscriptResult
        """
        if self._model is None:
            self.load_model()

        try:
            logger.info(f"STT 시작: {audio_path}")
            self._report_progress(0.0, "STT 처리 중...")

            transcribe_options = {
                "word_timestamps": True,
                "beam_size": 5,
            }

            if language and language != "auto":
                transcribe_options["language"] = language

            segments_gen, info = self._model.transcribe(
                str(audio_path), **transcribe_options
            )

            detected_lang = info.language
            lang_prob = info.language_probability
            duration = info.duration
            logger.info(
                f"감지 언어: {detected_lang} ({lang_prob:.1%}), 길이: {duration:.1f}초"
            )

            segments = []
            for seg in segments_gen:
                words = []
                if seg.words:
                    words = [
                        WordSegment(
                            word=w.word.strip(),
                            start=w.start,
                            end=w.end,
                            probability=w.probability,
                        )
                        for w in seg.words
                    ]

                segments.append(TranscriptSegment(
                    text=seg.text.strip(),
                    start=seg.start,
                    end=seg.end,
                    words=words,
                ))

                if duration > 0:
                    progress = min(seg.end / duration, 1.0)
                    self._report_progress(
                        progress, f"STT 처리 중... {progress*100:.0f}%"
                    )

            logger.info(f"STT 완료: {len(segments)}개 세그먼트")
            self._report_progress(1.0, "STT 완료")

            return TranscriptResult(
                segments=segments,
                language=detected_lang,
                language_probability=lang_prob,
                duration=duration,
            )

        except Exception as e:
            raise TranscribeError(f"STT 처리 실패: {e}")

    def transcribe_with_vad(
        self,
        audio_path: Path,
        language: Optional[str] = None,
    ) -> TranscriptResult:
        """VAD(Voice Activity Detection) 필터를 적용하여 전사.

        Silero VAD를 사용해 비음성 구간을 스킵하여 정확도 향상.
        """
        if self._model is None:
            self.load_model()

        try:
            logger.info(f"VAD + STT 시작: {audio_path}")
            self._report_progress(0.0, "VAD + STT 처리 중...")

            transcribe_options = {
                "word_timestamps": True,
                "beam_size": 5,
                "vad_filter": True,
                "vad_parameters": {
                    "min_silence_duration_ms": 500,
                    "speech_pad_ms": 200,
                },
            }

            if language and language != "auto":
                transcribe_options["language"] = language

            segments_gen, info = self._model.transcribe(
                str(audio_path), **transcribe_options
            )

            detected_lang = info.language
            lang_prob = info.language_probability
            duration = info.duration

            segments = []
            for seg in segments_gen:
                words = []
                if seg.words:
                    words = [
                        WordSegment(
                            word=w.word.strip(),
                            start=w.start,
                            end=w.end,
                            probability=w.probability,
                        )
                        for w in seg.words
                    ]

                segments.append(TranscriptSegment(
                    text=seg.text.strip(),
                    start=seg.start,
                    end=seg.end,
                    words=words,
                ))

                if duration > 0:
                    progress = min(seg.end / duration, 1.0)
                    self._report_progress(
                        progress, f"VAD+STT 처리 중... {progress*100:.0f}%"
                    )

            logger.info(f"VAD+STT 완료: {len(segments)}개 세그먼트")
            self._report_progress(1.0, "VAD+STT 완료")

            return TranscriptResult(
                segments=segments,
                language=detected_lang,
                language_probability=lang_prob,
                duration=duration,
            )

        except Exception as e:
            raise TranscribeError(f"VAD+STT 처리 실패: {e}")

    def _report_progress(self, ratio: float, text: str):
        if self._progress_callback:
            self._progress_callback(ratio, text)

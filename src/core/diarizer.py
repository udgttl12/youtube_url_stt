"""화자 분리(Speaker Diarization) 모듈 - pyannote.audio 기반."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from src.utils.exceptions import CancelledError, DiarizeError, ModelLoadError
from src.utils.paths import get_pyannote_config_path

logger = logging.getLogger(__name__)


@dataclass
class DiarizeSegment:
    """화자 분리 세그먼트."""
    speaker: str
    start: float
    end: float


@dataclass
class DiarizeResult:
    """화자 분리 결과."""
    segments: List[DiarizeSegment]
    num_speakers: int


class SpeakerDiarizer:
    """pyannote.audio 기반 화자 분리 엔진."""

    def __init__(
        self,
        hf_token: str = "",
        device: str = "cpu",
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ):
        self._hf_token = hf_token
        self._device = device
        self._progress_callback = progress_callback
        self._cancel_check = cancel_check
        self._pipeline = None

    def load_model(self):
        """pyannote 화자 분리 파이프라인 로드.

        1차: 로컬 번들 모델 (resources/pyannote/) 시도
        2차: HuggingFace Hub 폴백
        """
        try:
            from pyannote.audio import Pipeline
            import torch

            logger.info("화자 분리 모델 로드 중...")
            self._report_progress(0.0, "화자 분리 모델 로드 중...")

            # 1차: 로컬 번들 모델
            local_config = get_pyannote_config_path()
            if local_config and local_config.exists():
                logger.info(f"로컬 번들 pyannote 모델 사용: {local_config}")
                # config.yaml 내 상대경로 해석을 위해 CWD를 모델 디렉토리로 변경
                cwd = Path.cwd()
                os.chdir(local_config.parent)
                try:
                    self._pipeline = Pipeline.from_pretrained(local_config)
                finally:
                    os.chdir(cwd)
            else:
                # 2차: HuggingFace Hub
                logger.info("HuggingFace Hub에서 pyannote 모델 로드")
                self._pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    token=self._hf_token if self._hf_token else None,
                )

            # 디바이스 설정
            if self._device == "cuda" and torch.cuda.is_available():
                self._pipeline.to(torch.device("cuda"))
                logger.info("화자 분리 모델: GPU 사용")
            else:
                logger.info("화자 분리 모델: CPU 사용")

            self._report_progress(1.0, "화자 분리 모델 로드 완료")

        except Exception as e:
            raise ModelLoadError(f"화자 분리 모델 로드 실패: {e}")

    def diarize(
        self,
        audio_path: Path,
        num_speakers: Optional[int] = None,
    ) -> DiarizeResult:
        """오디오 파일에서 화자 분리 수행.

        Args:
            audio_path: 전처리된 WAV 파일
            num_speakers: 화자 수 (None이면 자동 감지)

        Returns:
            DiarizeResult

        Raises:
            DiarizeError: 화자 분리 실패
        """
        if self._pipeline is None:
            self.load_model()

        try:
            import torch
            import torchaudio

            logger.info(f"화자 분리 시작: {audio_path}")
            self._report_progress(0.0, "화자 분리 처리 중...")

            diarize_params = {}
            if num_speakers is not None and num_speakers > 0:
                diarize_params["num_speakers"] = num_speakers
                logger.info(f"화자 수 지정: {num_speakers}")

            # torchaudio로 오디오를 인메모리 로드하여 전달
            # (torchcodec/AudioDecoder가 없어도 동작)
            waveform, sample_rate = torchaudio.load(str(audio_path))
            audio_input = {
                "waveform": waveform,
                "sample_rate": sample_rate,
                "uri": audio_path.stem,
            }

            hook = self._create_hook()
            if hook is not None:
                diarize_params["hook"] = hook

            result = self._pipeline(audio_input, **diarize_params)

            # pyannote 4.x는 DiarizeOutput, 3.x는 Annotation 반환
            if hasattr(result, "speaker_diarization"):
                diarization = result.speaker_diarization
            else:
                diarization = result

            segments = []
            speakers_set = set()

            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append(DiarizeSegment(
                    speaker=speaker,
                    start=turn.start,
                    end=turn.end,
                ))
                speakers_set.add(speaker)

            # 화자 라벨 정규화 (SPEAKER_00 → SPEAKER_0 형식)
            speaker_map = {
                s: f"SPEAKER_{i}" for i, s in enumerate(sorted(speakers_set))
            }
            for seg in segments:
                seg.speaker = speaker_map.get(seg.speaker, seg.speaker)

            num_detected = len(speakers_set)
            logger.info(
                f"화자 분리 완료: {num_detected}명 감지, {len(segments)}개 구간"
            )
            self._report_progress(1.0, f"화자 분리 완료 ({num_detected}명)")

            return DiarizeResult(
                segments=segments,
                num_speakers=num_detected,
            )

        except CancelledError:
            raise
        except Exception as e:
            raise DiarizeError(f"화자 분리 실패: {e}")

    def _create_hook(self):
        """pyannote hook 콜백을 생성하여 내부 단계별 진행률을 보고.

        pyannote Pipeline의 hook 시그니처:
            hook(step_name, step_artefact, file=file, completed=N, total=M)

        단계별 진행률 범위:
            segmentation:          0.05 ~ 0.50
            speaker_counting:      0.55
            embeddings:            0.55 ~ 0.90
            discrete_diarization:  0.95
        """
        if not self._progress_callback and not self._cancel_check:
            return None

        stage_ranges = {
            "segmentation": (0.05, 0.50),
            "embeddings": (0.55, 0.90),
        }
        stage_messages = {
            "segmentation": "세그멘테이션 처리 중",
            "speaker_counting": "화자 수 추정 완료",
            "embeddings": "임베딩 추출 처리 중",
            "discrete_diarization": "클러스터링 완료",
        }
        reported_stages = set()

        def hook(step_name, step_artefact, file=None, completed=None, total=None):
            if self._cancel_check and self._cancel_check():
                raise CancelledError()

            if not self._progress_callback:
                return

            msg = stage_messages.get(step_name, step_name)

            if step_name in stage_ranges and completed is not None and total is not None and total > 0:
                start, end = stage_ranges[step_name]
                batch_ratio = completed / total
                progress = start + (end - start) * batch_ratio
                pct = int(batch_ratio * 100)
                self._report_progress(progress, f"{msg}... {pct}%")
            elif step_name not in reported_stages:
                reported_stages.add(step_name)
                if step_name == "speaker_counting":
                    self._report_progress(0.55, msg)
                elif step_name == "discrete_diarization":
                    self._report_progress(0.95, msg)

        return hook

    def _report_progress(self, ratio: float, text: str):
        if self._progress_callback:
            self._progress_callback(ratio, text)

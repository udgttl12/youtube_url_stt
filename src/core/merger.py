"""STT 결과와 화자 분리 결과 병합 모듈."""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from src.core.transcriber import TranscriptResult, TranscriptSegment, WordSegment
from src.core.diarizer import DiarizeResult, DiarizeSegment
from src.utils.exceptions import MergeError

logger = logging.getLogger(__name__)


@dataclass
class MergedSegment:
    """병합된 세그먼트 (화자 + 텍스트 + 시간)."""
    speaker: str
    text: str
    start: float
    end: float
    words: List[WordSegment] = field(default_factory=list)


@dataclass
class MergedResult:
    """최종 병합 결과."""
    segments: List[MergedSegment]
    num_speakers: int
    language: str = ""
    duration: float = 0.0


class ResultMerger:
    """STT 단어 타임스탬프와 화자 구간을 시간축 매핑으로 병합.

    방법 A: 전체 오디오 한 번에 STT → 화자 분리 결과와 사후 매핑
    - 문맥 유지로 STT 정확도 우수
    - 각 단어의 시간 정보를 화자 구간에 매핑
    """

    @staticmethod
    def merge(
        transcript: TranscriptResult,
        diarize: Optional[DiarizeResult] = None,
    ) -> MergedResult:
        """STT 결과와 화자 분리 결과를 병합.

        Args:
            transcript: STT 전사 결과
            diarize: 화자 분리 결과 (None이면 단일 화자)

        Returns:
            MergedResult
        """
        try:
            if diarize is None or not diarize.segments:
                # 화자 분리 없음 → 단일 화자로 처리
                logger.info("화자 분리 결과 없음, 단일 화자로 처리")
                return ResultMerger._single_speaker_merge(transcript)

            # 단어 단위 화자 매핑
            logger.info("단어-화자 매핑 시작")
            return ResultMerger._word_level_merge(transcript, diarize)

        except Exception as e:
            raise MergeError(f"결과 병합 실패: {e}")

    @staticmethod
    def _single_speaker_merge(transcript: TranscriptResult) -> MergedResult:
        """단일 화자로 병합."""
        segments = []
        for seg in transcript.segments:
            segments.append(MergedSegment(
                speaker="SPEAKER_0",
                text=seg.text,
                start=seg.start,
                end=seg.end,
                words=seg.words,
            ))

        return MergedResult(
            segments=segments,
            num_speakers=1,
            language=transcript.language,
            duration=transcript.duration,
        )

    @staticmethod
    def _word_level_merge(
        transcript: TranscriptResult,
        diarize: DiarizeResult,
    ) -> MergedResult:
        """단어 단위로 화자를 매핑하고, 같은 화자의 연속 단어를 묶음."""

        # 1. 모든 단어에 화자 할당
        all_words: List[WordSegment] = []
        for seg in transcript.segments:
            if seg.words:
                all_words.extend(seg.words)
            else:
                # 단어 타임스탬프 없으면 세그먼트 전체를 하나의 단어로 취급
                all_words.append(WordSegment(
                    word=seg.text,
                    start=seg.start,
                    end=seg.end,
                ))

        if not all_words:
            return MergedResult(
                segments=[],
                num_speakers=diarize.num_speakers,
                language=transcript.language,
                duration=transcript.duration,
            )

        # 2. 각 단어의 중간 시점으로 화자 결정
        word_speakers = []
        for word in all_words:
            mid_time = (word.start + word.end) / 2
            speaker = ResultMerger._find_speaker_at(mid_time, diarize.segments)
            word_speakers.append((word, speaker))

        # 3. 같은 화자의 연속 단어를 하나의 세그먼트로 그룹화
        merged_segments: List[MergedSegment] = []
        current_speaker = None
        current_words: List[WordSegment] = []
        current_text_parts: List[str] = []

        for word, speaker in word_speakers:
            if speaker != current_speaker and current_words:
                # 이전 그룹 완성
                merged_segments.append(MergedSegment(
                    speaker=current_speaker or "SPEAKER_0",
                    text=" ".join(current_text_parts).strip(),
                    start=current_words[0].start,
                    end=current_words[-1].end,
                    words=list(current_words),
                ))
                current_words = []
                current_text_parts = []

            current_speaker = speaker
            current_words.append(word)
            current_text_parts.append(word.word)

        # 마지막 그룹
        if current_words:
            merged_segments.append(MergedSegment(
                speaker=current_speaker or "SPEAKER_0",
                text=" ".join(current_text_parts).strip(),
                start=current_words[0].start,
                end=current_words[-1].end,
                words=list(current_words),
            ))

        logger.info(
            f"병합 완료: {len(merged_segments)}개 세그먼트, "
            f"{diarize.num_speakers}명 화자"
        )

        return MergedResult(
            segments=merged_segments,
            num_speakers=diarize.num_speakers,
            language=transcript.language,
            duration=transcript.duration,
        )

    @staticmethod
    def _find_speaker_at(time_point: float, diar_segments: List[DiarizeSegment]) -> str:
        """주어진 시간에 해당하는 화자를 찾음."""
        best_speaker = "SPEAKER_0"
        min_distance = float("inf")

        for seg in diar_segments:
            if seg.start <= time_point <= seg.end:
                return seg.speaker

            # 가장 가까운 구간의 화자로 폴백
            dist = min(abs(time_point - seg.start), abs(time_point - seg.end))
            if dist < min_distance:
                min_distance = dist
                best_speaker = seg.speaker

        return best_speaker

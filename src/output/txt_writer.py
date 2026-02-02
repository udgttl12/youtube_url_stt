"""TXT 포맷 출력 - 회의록/대담 기록 형식."""

from pathlib import Path

from src.core.merger import MergedResult, MergedSegment
from src.output.formatter import BaseFormatter


def _format_time(seconds: float) -> str:
    """초를 HH:MM:SS 형식으로 변환."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class TxtFormatter(BaseFormatter):
    """TXT 회의록 형식 포맷터.

    출력 예시:
        [00:00:02 - 00:00:07] SPEAKER_0
        안녕하세요 오늘 회의 시작하겠습니다.

        [00:00:07 - 00:00:12] SPEAKER_1
        네, 자료 공유드리겠습니다.
    """

    @property
    def extension(self) -> str:
        return ".txt"

    def format(self, result: MergedResult) -> str:
        lines = []
        lines.append(f"# 음성 전사 결과")
        lines.append(f"# 화자 수: {result.num_speakers}")
        if result.language:
            lines.append(f"# 언어: {result.language}")
        if result.duration > 0:
            lines.append(f"# 길이: {_format_time(result.duration)}")
        lines.append("")
        lines.append("=" * 60)
        lines.append("")

        for seg in result.segments:
            start = _format_time(seg.start)
            end = _format_time(seg.end)
            lines.append(f"[{start} - {end}] {seg.speaker}")
            lines.append(seg.text)
            lines.append("")

        return "\n".join(lines)

    def save(self, result: MergedResult, output_path: Path) -> Path:
        output_path = output_path.with_suffix(self.extension)
        content = self.format(result)
        output_path.write_text(content, encoding="utf-8")
        return output_path

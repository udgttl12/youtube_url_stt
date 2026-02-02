"""SRT 자막 포맷 출력."""

from pathlib import Path

from src.core.merger import MergedResult
from src.output.formatter import BaseFormatter


def _format_srt_time(seconds: float) -> str:
    """초를 SRT 타임코드 형식 (HH:MM:SS,mmm)으로 변환."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class SrtFormatter(BaseFormatter):
    """SRT 자막 포맷터.

    출력 예시:
        1
        00:00:02,000 --> 00:00:07,500
        [SPEAKER_0] 안녕하세요 오늘 회의 시작하겠습니다.

        2
        00:00:07,500 --> 00:00:12,000
        [SPEAKER_1] 네, 자료 공유드리겠습니다.
    """

    @property
    def extension(self) -> str:
        return ".srt"

    def format(self, result: MergedResult) -> str:
        lines = []

        for i, seg in enumerate(result.segments, 1):
            start = _format_srt_time(seg.start)
            end = _format_srt_time(seg.end)
            lines.append(str(i))
            lines.append(f"{start} --> {end}")
            if result.num_speakers > 1:
                lines.append(f"[{seg.speaker}] {seg.text}")
            else:
                lines.append(seg.text)
            lines.append("")

        return "\n".join(lines)

    def save(self, result: MergedResult, output_path: Path) -> Path:
        output_path = output_path.with_suffix(self.extension)
        content = self.format(result)
        output_path.write_text(content, encoding="utf-8")
        return output_path

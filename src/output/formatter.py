"""출력 포맷터 모듈 — MergedResult를 txt/srt/json으로 변환."""

import json
from abc import ABC, abstractmethod
from pathlib import Path

from src.core.merger import MergedResult


class BaseFormatter(ABC):
    """포맷터 기본 클래스."""

    @property
    @abstractmethod
    def extension(self) -> str:
        ...

    @abstractmethod
    def format(self, result: MergedResult) -> str:
        ...

    def save(self, result: MergedResult, path: Path) -> None:
        path.write_text(self.format(result), encoding="utf-8")


class TxtFormatter(BaseFormatter):
    """사람 읽기용 텍스트 포맷."""

    extension = ".txt"

    def format(self, result: MergedResult) -> str:
        lines = []
        for seg in result.segments:
            start = _fmt_time(seg.start)
            end = _fmt_time(seg.end)
            lines.append(f"[{start} - {end}] {seg.speaker}")
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines)


class SrtFormatter(BaseFormatter):
    """SRT 자막 포맷."""

    extension = ".srt"

    def format(self, result: MergedResult) -> str:
        lines = []
        for i, seg in enumerate(result.segments, 1):
            start = _fmt_srt_time(seg.start)
            end = _fmt_srt_time(seg.end)
            lines.append(str(i))
            lines.append(f"{start} --> {end}")
            lines.append(f"[{seg.speaker}] {seg.text}")
            lines.append("")
        return "\n".join(lines)


class JsonFormatter(BaseFormatter):
    """구조화 JSON 포맷."""

    extension = ".json"

    def format(self, result: MergedResult) -> str:
        data = {
            "metadata": {
                "num_speakers": result.num_speakers,
                "language": result.language,
                "duration": result.duration,
            },
            "segments": [
                {
                    "speaker": seg.speaker,
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": seg.text,
                }
                for seg in result.segments
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


_FORMATTERS = {
    "txt": TxtFormatter,
    "srt": SrtFormatter,
    "json": JsonFormatter,
}


def get_formatter(format_type: str) -> BaseFormatter:
    """포맷 타입에 해당하는 포맷터 인스턴스 반환.

    Args:
        format_type: 'txt', 'srt', 'json'

    Returns:
        BaseFormatter 인스턴스

    Raises:
        ValueError: 지원하지 않는 포맷
    """
    cls = _FORMATTERS.get(format_type)
    if cls is None:
        raise ValueError(
            f"지원하지 않는 포맷: {format_type} "
            f"(가능: {', '.join(_FORMATTERS)})"
        )
    return cls()


def _fmt_time(seconds: float) -> str:
    """초를 HH:MM:SS 형식으로 변환."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _fmt_srt_time(seconds: float) -> str:
    """초를 SRT 시간 형식(HH:MM:SS,mmm)으로 변환."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

"""JSON 구조화 데이터 출력."""

import json
from pathlib import Path
from datetime import datetime

from src.core.merger import MergedResult
from src.output.formatter import BaseFormatter


class JsonFormatter(BaseFormatter):
    """JSON 구조화 포맷터.

    출력 구조:
        {
            "metadata": { ... },
            "segments": [
                {
                    "speaker": "SPEAKER_0",
                    "start": 2.0,
                    "end": 7.5,
                    "text": "..."
                }
            ]
        }
    """

    @property
    def extension(self) -> str:
        return ".json"

    def format(self, result: MergedResult) -> str:
        data = {
            "metadata": {
                "num_speakers": result.num_speakers,
                "language": result.language,
                "duration": round(result.duration, 2),
                "total_segments": len(result.segments),
                "created_at": datetime.now().isoformat(),
            },
            "segments": [
                {
                    "speaker": seg.speaker,
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "text": seg.text,
                    "words": [
                        {
                            "word": w.word,
                            "start": round(w.start, 3),
                            "end": round(w.end, 3),
                            "probability": round(w.probability, 4),
                        }
                        for w in seg.words
                    ] if seg.words else [],
                }
                for seg in result.segments
            ],
        }

        return json.dumps(data, ensure_ascii=False, indent=2)

    def save(self, result: MergedResult, output_path: Path) -> Path:
        output_path = output_path.with_suffix(self.extension)
        content = self.format(result)
        output_path.write_text(content, encoding="utf-8")
        return output_path

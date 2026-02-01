"""설정 관리 (HuggingFace 토큰 등)."""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from src.utils.paths import get_config_path

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """애플리케이션 설정."""
    hf_token: str = ""
    language: str = "auto"          # "auto" 또는 "ko", "en" 등
    num_speakers: Optional[int] = None  # None = 자동 감지
    output_format: str = "txt"      # "txt", "srt", "json"
    high_accuracy: bool = False     # 고정밀 모드
    output_dir: str = ""            # 빈 문자열이면 기본 경로 사용
    last_output_dir: str = ""
    setup_completed: bool = False

    def save(self):
        """설정을 파일에 저장."""
        config_path = get_config_path()
        try:
            data = asdict(self)
            config_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.debug(f"설정 저장: {config_path}")
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")

    @classmethod
    def load(cls) -> "AppConfig":
        """파일에서 설정을 로드."""
        config_path = get_config_path()
        if not config_path.exists():
            return cls()

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            # 알려진 필드만 사용
            known_fields = {f.name for f in cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in known_fields}
            return cls(**filtered)
        except Exception as e:
            logger.warning(f"설정 로드 실패, 기본값 사용: {e}")
            return cls()

    def has_hf_token(self) -> bool:
        """HuggingFace 토큰이 설정되어 있는지 확인."""
        return bool(self.hf_token and self.hf_token.strip())

    def resolve_hf_token(self, cli_token: str = "") -> str:
        """HuggingFace 토큰을 우선순위에 따라 반환.

        우선순위:
        1. CLI 인자로 전달된 토큰
        2. HF_TOKEN 환경변수
        3. HUGGING_FACE_HUB_TOKEN 환경변수
        4. 저장된 설정의 토큰
        """
        if cli_token and cli_token.strip():
            return cli_token.strip()

        env_token = os.environ.get("HF_TOKEN", "").strip()
        if env_token:
            return env_token

        hub_token = os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
        if hub_token:
            return hub_token

        return self.hf_token.strip() if self.hf_token else ""

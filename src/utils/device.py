"""GPU/CPU 감지 및 모델 설정 관리."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 지원 Whisper 모델 목록
WHISPER_MODELS = [
    "tiny", "base", "small", "medium", "large-v3",
    "distil-large-v3", "distil-medium.en", "distil-small.en",
]


@dataclass
class DeviceConfig:
    """디바이스 설정."""
    device: str              # "cuda" 또는 "cpu"
    compute_type: str        # "float16", "int8", "float32"
    whisper_model: str       # "large-v3", "distil-large-v3", "small" 등
    recommended_beam_size: int = 5
    gpu_name: str = ""
    gpu_memory_gb: float = 0.0


class DeviceManager:
    """하드웨어 감지 및 최적 설정 결정."""

    @staticmethod
    def detect(
        force_cpu: bool = False,
        whisper_model_override: str = "",
    ) -> DeviceConfig:
        """시스템 하드웨어를 감지하고 최적 설정을 반환.

        Args:
            force_cpu: CPU 모드 강제 사용
            whisper_model_override: 사용자 지정 Whisper 모델 (빈 문자열이면 자동 추천)
        """
        if force_cpu:
            logger.info("CPU 모드 강제 사용")
            model = whisper_model_override if whisper_model_override else "small"
            return DeviceConfig(
                device="cpu",
                compute_type="int8",
                whisper_model=model,
                recommended_beam_size=1,
            )

        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                gpu_mem = getattr(props, 'total_memory', getattr(props, 'total_mem', 0)) / (1024**3)
                logger.info(f"GPU 감지: {gpu_name} ({gpu_mem:.1f}GB)")

                # VRAM 티어별 최적 설정
                model, compute_type, beam_size = DeviceManager._select_by_vram(gpu_mem)

                if whisper_model_override:
                    model = whisper_model_override
                    logger.info(f"사용자 지정 모델 사용: {model}")

                config = DeviceConfig(
                    device="cuda",
                    compute_type=compute_type,
                    whisper_model=model,
                    recommended_beam_size=beam_size,
                    gpu_name=gpu_name,
                    gpu_memory_gb=gpu_mem,
                )
                logger.info(
                    f"자동 선택: {config.whisper_model} / {config.compute_type} / "
                    f"beam_size={config.recommended_beam_size}"
                )
                return config

        except ImportError:
            logger.warning("PyTorch가 설치되지 않음, CPU 모드 사용")
        except Exception as e:
            logger.warning(f"GPU 감지 실패: {e}, CPU 모드 사용")

        model = whisper_model_override if whisper_model_override else "small"
        return DeviceConfig(
            device="cpu",
            compute_type="int8",
            whisper_model=model,
            recommended_beam_size=1,
        )

    @staticmethod
    def _select_by_vram(gpu_mem_gb: float) -> tuple:
        """VRAM 용량에 따라 (모델, compute_type, beam_size) 반환.

        | VRAM      | 모델             | compute_type | beam_size |
        |-----------|-----------------|-------------|-----------|
        | >= 12GB   | large-v3        | float16     | 5         |
        | 8~12GB    | distil-large-v3 | float16     | 3         |
        | 6~8GB     | small           | float16     | 3         |
        | < 6GB     | small           | int8        | 1         |
        """
        if gpu_mem_gb >= 12:
            return ("large-v3", "float16", 5)
        elif gpu_mem_gb >= 8:
            return ("distil-large-v3", "float16", 3)
        elif gpu_mem_gb >= 6:
            return ("small", "float16", 3)
        else:
            return ("small", "int8", 1)

    @staticmethod
    def get_device_info_text(config: DeviceConfig) -> str:
        """디바이스 정보를 사용자 표시용 텍스트로 반환."""
        if config.device == "cuda":
            return (
                f"GPU: {config.gpu_name} ({config.gpu_memory_gb:.1f}GB)\n"
                f"모델: {config.whisper_model} ({config.compute_type})"
            )
        return (
            f"CPU 모드\n"
            f"모델: {config.whisper_model} ({config.compute_type})"
        )

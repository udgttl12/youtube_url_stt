"""GPU/CPU 감지 및 모델 설정 관리."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeviceConfig:
    """디바이스 설정."""
    device: str              # "cuda" 또는 "cpu"
    compute_type: str        # "float16", "int8", "float32"
    whisper_model: str       # "large-v3" 또는 "medium"
    gpu_name: str = ""
    gpu_memory_gb: float = 0.0


class DeviceManager:
    """하드웨어 감지 및 최적 설정 결정."""

    @staticmethod
    def detect(force_cpu: bool = False) -> DeviceConfig:
        """시스템 하드웨어를 감지하고 최적 설정을 반환."""
        if force_cpu:
            logger.info("CPU 모드 강제 사용")
            return DeviceConfig(
                device="cpu",
                compute_type="int8",
                whisper_model="large-v3",
            )

        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                gpu_mem = torch.cuda.get_device_properties(0).total_mem / (1024**3)
                logger.info(f"GPU 감지: {gpu_name} ({gpu_mem:.1f}GB)")

                return DeviceConfig(
                    device="cuda",
                    compute_type="float16",
                    whisper_model="large-v3",
                    gpu_name=gpu_name,
                    gpu_memory_gb=gpu_mem,
                )
        except ImportError:
            logger.warning("PyTorch가 설치되지 않음, CPU 모드 사용")
        except Exception as e:
            logger.warning(f"GPU 감지 실패: {e}, CPU 모드 사용")

        return DeviceConfig(
            device="cpu",
            compute_type="int8",
            whisper_model="large-v3",
        )

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

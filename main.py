"""YouTube 화자 분리 + STT 프로그램 진입점.

사용법:
    GUI 모드: python main.py
    CLI 모드: python main.py --cli --url <URL> [옵션]
"""

import argparse
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def run_cli(args):
    """CLI 모드 실행."""
    from src.utils.logger import setup_logger
    from src.utils.device import DeviceManager
    from src.utils.config import AppConfig
    from src.core.pipeline import Pipeline, PipelineConfig, PipelineStage
    from src.output.formatter import get_formatter

    # 로거 설정
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger(level=log_level)
    logger = logging.getLogger("youtube_stt")

    logger.info("=" * 60)
    logger.info("YouTube 화자 분리 + STT (CLI 모드)")
    logger.info("=" * 60)

    # 디바이스 감지
    device_config = DeviceManager.detect(force_cpu=args.cpu)
    logger.info(DeviceManager.get_device_info_text(device_config))

    # 설정 로드
    config = AppConfig.load()
    hf_token = args.hf_token or config.hf_token

    # 파이프라인 실행
    pipeline_config = PipelineConfig(
        url=args.url,
        language=args.language,
        num_speakers=args.speakers,
        output_format=args.format,
        enable_diarization=not args.no_diarize,
        use_vad=not args.no_vad,
        hf_token=hf_token,
    )

    def on_stage(stage: PipelineStage, progress: float, message: str):
        logger.info(f"[{stage.value}] {message}")

    pipeline = Pipeline(
        config=pipeline_config,
        stage_callback=on_stage,
        device_config=device_config,
    )

    result = pipeline.run()

    # 결과 출력
    formatter = get_formatter(args.format)
    formatted = formatter.format(result)

    if args.output:
        output_path = Path(args.output)
        formatter.save(result, output_path)
        logger.info(f"결과 저장: {output_path}")
    else:
        print("\n" + formatted)

    logger.info("완료!")


def run_gui():
    """GUI 모드 실행."""
    from src.gui.app import App

    app = App()
    app.mainloop()


def main():
    parser = argparse.ArgumentParser(
        description="YouTube 화자 분리 + STT 프로그램",
    )
    parser.add_argument(
        "--cli", action="store_true",
        help="CLI 모드로 실행",
    )
    parser.add_argument(
        "--url", type=str,
        help="YouTube URL",
    )
    parser.add_argument(
        "--language", type=str, default="auto",
        help="언어 코드 (auto, ko, en 등)",
    )
    parser.add_argument(
        "--speakers", type=int, default=None,
        help="화자 수 (미지정 시 자동 감지)",
    )
    parser.add_argument(
        "--format", type=str, default="txt",
        choices=["txt", "srt", "json"],
        help="출력 포맷",
    )
    parser.add_argument(
        "--output", "-o", type=str,
        help="출력 파일 경로",
    )
    parser.add_argument(
        "--hf-token", type=str,
        help="HuggingFace 토큰 (화자 분리용)",
    )
    parser.add_argument(
        "--no-diarize", action="store_true",
        help="화자 분리 비활성화",
    )
    parser.add_argument(
        "--no-vad", action="store_true",
        help="VAD 필터 비활성화",
    )
    parser.add_argument(
        "--cpu", action="store_true",
        help="CPU 모드 강제 사용",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="상세 로그 출력",
    )

    args = parser.parse_args()

    if args.cli:
        if not args.url:
            parser.error("CLI 모드에서는 --url이 필수입니다")
        run_cli(args)
    else:
        run_gui()


if __name__ == "__main__":
    main()

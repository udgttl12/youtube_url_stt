"""YouTube 화자 분리 + STT 프로그램 진입점.

사용법:
    GUI 모드: python main.py
    CLI 모드: python main.py --cli --url <URL> [옵션]
    셋업:    python main.py --setup [--hf-token TOKEN]
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

    # 모델 오버라이드
    model_override = "" if args.model == "auto" else args.model

    # 디바이스 감지
    device_config = DeviceManager.detect(
        force_cpu=args.cpu,
        whisper_model_override=model_override,
    )
    logger.info(DeviceManager.get_device_info_text(device_config))

    # 설정 로드
    config = AppConfig.load()
    hf_token = config.resolve_hf_token(cli_token=args.hf_token or "")

    # 파이프라인 실행
    pipeline_config = PipelineConfig(
        url=args.url,
        language=args.language,
        num_speakers=args.speakers,
        output_format=args.format,
        enable_diarization=not args.no_diarize,
        use_vad=not args.no_vad,
        low_power=args.low_power,
        hf_token=hf_token,
        whisper_model=model_override,
        beam_size=args.beam_size,
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


def run_setup_cli(args):
    """CLI 셋업 모드 — 의존성 사전 다운로드."""
    from src.utils.logger import setup_logger
    from src.utils.config import AppConfig
    from src.utils.dependency import run_setup

    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger(level=log_level)
    logger = logging.getLogger("youtube_stt")

    logger.info("=" * 60)
    logger.info("의존성 셋업 시작")
    logger.info("=" * 60)

    config = AppConfig.load()
    hf_token = config.resolve_hf_token(cli_token=args.hf_token or "")

    def progress_callback(ratio, message):
        logger.info(f"  [{ratio * 100:.0f}%] {message}")

    results = run_setup(hf_token=hf_token, progress_callback=progress_callback)

    logger.info("=" * 60)
    logger.info("셋업 결과:")
    for key, status in results.items():
        logger.info(f"  {key}: {status}")
    logger.info("=" * 60)


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
        "--low-power", action="store_true",
        help="저사양 모드 (스레드/빔 축소로 자원 사용량 감소)",
    )
    parser.add_argument(
        "--model", type=str, default="auto",
        choices=[
            "auto", "tiny", "base", "small", "medium", "large-v3",
            "distil-large-v3", "distil-medium.en", "distil-small.en",
        ],
        help="Whisper 모델 선택 (auto=VRAM 기반 자동 추천)",
    )
    parser.add_argument(
        "--beam-size", type=int, default=0,
        help="Beam size (0=자동 추천)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="상세 로그 출력",
    )
    parser.add_argument(
        "--setup", action="store_true",
        help="의존성(ffmpeg, 모델) 사전 다운로드 실행",
    )

    args = parser.parse_args()

    if args.setup:
        run_setup_cli(args)
    elif args.cli:
        if not args.url:
            parser.error("CLI 모드에서는 --url이 필수입니다")
        run_cli(args)
    else:
        run_gui()


if __name__ == "__main__":
    main()

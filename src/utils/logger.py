"""로깅 설정."""

import logging
import sys
from typing import Callable, Optional


class GUILogHandler(logging.Handler):
    """GUI 로그 뷰어로 로그를 전달하는 핸들러."""

    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self._callback = callback

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self._callback(msg)
        except Exception:
            self.handleError(record)


def setup_logger(
    level: int = logging.INFO,
    gui_callback: Optional[Callable[[str], None]] = None,
) -> logging.Logger:
    """애플리케이션 로거를 설정하고 반환.

    Args:
        level: 로그 레벨
        gui_callback: GUI 로그 뷰어 콜백 (선택)

    Returns:
        설정된 루트 로거
    """
    root_logger = logging.getLogger("youtube_stt")
    root_logger.setLevel(level)

    # 기존 핸들러 제거
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # GUI 핸들러
    if gui_callback:
        gui_handler = GUILogHandler(gui_callback)
        gui_handler.setFormatter(formatter)
        root_logger.addHandler(gui_handler)

    return root_logger

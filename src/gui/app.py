"""메인 GUI 애플리케이션 - customtkinter 기반."""

import logging
import threading
from typing import Optional

import customtkinter as ctk

from src.core.pipeline import Pipeline, PipelineConfig, PipelineStage
from src.core.merger import MergedResult
from src.utils.config import AppConfig
from src.utils.device import DeviceManager, DeviceConfig
from src.utils.dependency import is_ffmpeg_available
from src.utils.logger import setup_logger
from src.gui.components.url_input import URLInputFrame
from src.gui.components.options_panel import OptionsPanelFrame
from src.gui.components.progress_bar import ProgressFrame
from src.gui.components.log_viewer import LogViewerFrame
from src.gui.components.result_preview import ResultPreviewFrame
from src.gui.setup_wizard import SetupWizard
from src.gui import fonts

logger = logging.getLogger(__name__)


class HFTokenDialog(ctk.CTkToplevel):
    """HuggingFace 토큰 입력 다이얼로그."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.title("HuggingFace 토큰 입력")
        self.geometry("500x220")
        self.resizable(False, False)
        self.result: Optional[str] = None

        self.grid_columnconfigure(0, weight=1)

        info_label = ctk.CTkLabel(
            self,
            text=(
                "화자 분리 기능을 사용하려면 HuggingFace 토큰이 필요합니다.\n"
                "https://huggingface.co/settings/tokens 에서 발급받을 수 있습니다.\n"
                "(화자 분리를 사용하지 않으려면 비워두세요)"
            ),
            font=fonts.small_font(),
            justify="left",
            wraplength=460,
        )
        info_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.token_entry = ctk.CTkEntry(
            self,
            placeholder_text="hf_...",
            width=460,
            show="*",
        )
        self.token_entry.grid(row=1, column=0, padx=20, pady=10)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=20, pady=(10, 20))

        ctk.CTkButton(
            btn_frame, text="확인", width=100,
            command=self._on_ok,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="건너뛰기", width=100,
            fg_color="gray40",
            command=self._on_skip,
        ).pack(side="left", padx=5)

        self.grab_set()

    def _on_ok(self):
        self.result = self.token_entry.get().strip()
        self.destroy()

    def _on_skip(self):
        self.result = ""
        self.destroy()


class App(ctk.CTk):
    """메인 애플리케이션 윈도우."""

    def __init__(self):
        super().__init__()

        self.title("YouTube 화자 분리 + STT")
        self.geometry("950x750")
        self.minsize(800, 600)

        # 다크 모드
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # 설정 로드
        self._config = AppConfig.load()
        self._device_config: Optional[DeviceConfig] = None
        self._pipeline: Optional[Pipeline] = None
        self._pipeline_thread: Optional[threading.Thread] = None
        self._result: Optional[MergedResult] = None

        # 로거 설정
        self._logger = setup_logger(
            gui_callback=lambda msg: self.after(0, self._on_log, msg)
        )

        self._build_ui()
        self._detect_device()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # 로그/미리보기 영역 확장
        self.grid_rowconfigure(5, weight=2)

        # 제목 + 디바이스 정보
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header_frame,
            text="YouTube 화자 분리 + STT",
            font=fonts.title_font(),
        )
        title_label.grid(row=0, column=0, sticky="w")

        self.setup_btn = ctk.CTkButton(
            header_frame,
            text="설정",
            width=60,
            height=28,
            font=fonts.small_font(),
            fg_color="gray40",
            command=self._on_open_setup,
        )
        self.setup_btn.grid(row=0, column=1, padx=(10, 10), sticky="e")

        self.device_label = ctk.CTkLabel(
            header_frame,
            text="디바이스 감지 중...",
            font=fonts.small_font(),
            text_color="gray60",
        )
        self.device_label.grid(row=0, column=2, sticky="e")

        # URL 입력
        self.url_input = URLInputFrame(self)
        self.url_input.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        # 옵션 패널
        self.options_panel = OptionsPanelFrame(self, config=self._config)
        self.options_panel.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        # 실행/취소 버튼
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=15, pady=5, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)

        self.run_btn = ctk.CTkButton(
            btn_frame,
            text="실행",
            font=fonts.button_large_font(),
            height=42,
            command=self._on_run,
        )
        self.run_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.cancel_btn = ctk.CTkButton(
            btn_frame,
            text="취소",
            font=fonts.subheading_font(),
            height=42,
            width=100,
            fg_color="red",
            hover_color="darkred",
            state="disabled",
            command=self._on_cancel,
        )
        self.cancel_btn.grid(row=0, column=1)

        # 진행률
        self.progress = ProgressFrame(self)
        self.progress.grid(row=4, column=0, padx=15, pady=5, sticky="ew")

        # 하단 탭: 로그 / 미리보기
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=5, column=0, padx=15, pady=(5, 15), sticky="nsew")

        self.tab_view.add("로그")
        self.tab_view.add("결과 미리보기")

        # 로그 탭
        log_tab = self.tab_view.tab("로그")
        log_tab.grid_columnconfigure(0, weight=1)
        log_tab.grid_rowconfigure(0, weight=1)
        self.log_viewer = LogViewerFrame(log_tab)
        self.log_viewer.grid(row=0, column=0, sticky="nsew")

        # 결과 미리보기 탭
        preview_tab = self.tab_view.tab("결과 미리보기")
        preview_tab.grid_columnconfigure(0, weight=1)
        preview_tab.grid_rowconfigure(0, weight=1)
        self.result_preview = ResultPreviewFrame(preview_tab)
        self.result_preview.grid(row=0, column=0, sticky="nsew")

    def _detect_device(self):
        """백그라운드에서 디바이스 감지."""
        def detect():
            config = DeviceManager.detect()
            self.after(0, self._on_device_detected, config)

        threading.Thread(target=detect, daemon=True).start()

    def _on_device_detected(self, config: DeviceConfig):
        self._device_config = config
        info = DeviceManager.get_device_info_text(config)
        self.device_label.configure(text=info.replace("\n", " | "))
        logger.info(f"디바이스: {info}")

    def _on_open_setup(self):
        """설정 다이얼로그 열기."""
        SetupWizard(self, config=self._config)

    def _on_run(self):
        """실행 버튼 클릭."""
        url = self.url_input.get_url()
        if not url:
            self._show_error("YouTube URL을 입력해주세요.")
            return

        # ffmpeg 체크
        if not is_ffmpeg_available():
            self._show_ffmpeg_required()
            return

        # HF 토큰 확인 (화자 분리 활성화 시)
        if self.options_panel.is_diarization_enabled() and not self._config.resolve_hf_token():
            self._ask_hf_token(url)
            return

        self._start_pipeline(url)

    def _ask_hf_token(self, url: str):
        """HF 토큰 입력 다이얼로그."""
        dialog = HFTokenDialog(self)
        self.wait_window(dialog)

        if dialog.result is not None:
            self._config.hf_token = dialog.result
            self._config.save()

        self._start_pipeline(url)

    def _start_pipeline(self, url: str):
        """파이프라인 실행 시작."""
        # UI 비활성화
        self._set_ui_enabled(False)
        self.progress.reset()
        self.log_viewer.clear()
        self.result_preview.clear()

        # 파이프라인 설정
        pipeline_config = PipelineConfig(
            url=url,
            language=self.options_panel.get_language(),
            num_speakers=self.options_panel.get_num_speakers(),
            output_format=self.options_panel.get_output_format(),
            enable_diarization=self.options_panel.is_diarization_enabled(),
            use_vad=self.options_panel.is_vad_enabled(),
            hf_token=self._config.resolve_hf_token(),
        )

        self._pipeline = Pipeline(
            config=pipeline_config,
            stage_callback=lambda s, p, m: self.after(0, self._on_stage_update, s, p, m),
            device_config=self._device_config,
        )

        # 백그라운드 스레드에서 실행
        self._pipeline_thread = threading.Thread(
            target=self._run_pipeline,
            daemon=True,
        )
        self._pipeline_thread.start()

    def _run_pipeline(self):
        """백그라운드에서 파이프라인 실행."""
        try:
            result = self._pipeline.run()
            self.after(0, self._on_pipeline_done, result)
        except Exception as e:
            self.after(0, self._on_pipeline_error, str(e))

    def _on_stage_update(self, stage: PipelineStage, progress: float, message: str):
        """파이프라인 단계 업데이트 (GUI 스레드)."""
        self.progress.update_progress(stage, progress, message)

    def _on_pipeline_done(self, result: MergedResult):
        """파이프라인 완료."""
        self._result = result
        self._set_ui_enabled(True)

        # 결과 미리보기 표시
        fmt = self.options_panel.get_output_format()
        self.result_preview.set_result(result, fmt)
        self.tab_view.set("결과 미리보기")

        logger.info(f"처리 완료: {len(result.segments)}개 세그먼트, {result.num_speakers}명 화자")

    def _on_pipeline_error(self, error_msg: str):
        """파이프라인 오류."""
        self._set_ui_enabled(True)
        self.progress.update_progress(PipelineStage.ERROR, 0.0, f"오류: {error_msg}")
        logger.error(f"파이프라인 오류: {error_msg}")

    def _on_cancel(self):
        """취소 버튼 클릭."""
        if self._pipeline:
            self._pipeline.cancel()
            logger.info("처리 취소 요청됨")

    def _on_log(self, message: str):
        """로그 메시지 (GUI 스레드)."""
        self.log_viewer.append_log(message)

    def _set_ui_enabled(self, enabled: bool):
        """UI 요소 활성화/비활성화."""
        self.url_input.set_enabled(enabled)
        self.options_panel.set_enabled(enabled)
        self.run_btn.configure(state="normal" if enabled else "disabled")
        self.cancel_btn.configure(state="disabled" if enabled else "normal")

    def _show_error(self, message: str):
        """에러 메시지 다이얼로그."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("오류")
        dialog.geometry("400x150")
        dialog.resizable(False, False)

        ctk.CTkLabel(
            dialog,
            text=message,
            font=fonts.body_font(),
            wraplength=360,
        ).pack(pady=30)

        ctk.CTkButton(
            dialog, text="확인", width=100,
            command=dialog.destroy,
        ).pack()

        dialog.grab_set()

    def _show_ffmpeg_required(self):
        """ffmpeg 미설치 안내 다이얼로그."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("ffmpeg 필요")
        dialog.geometry("420x170")
        dialog.resizable(False, False)

        ctk.CTkLabel(
            dialog,
            text=(
                "ffmpeg가 설치되지 않았습니다.\n"
                "오디오 처리를 위해 ffmpeg가 필요합니다.\n"
                "설정에서 다운로드하시겠습니까?"
            ),
            font=fonts.body_font(),
            wraplength=380,
        ).pack(pady=(25, 15))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=5)

        def open_setup():
            dialog.destroy()
            self._on_open_setup()

        ctk.CTkButton(
            btn_frame, text="설정 열기", width=100,
            command=open_setup,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="취소", width=100,
            fg_color="gray40",
            command=dialog.destroy,
        ).pack(side="left", padx=5)

        dialog.grab_set()

"""의존성 관리 다이얼로그 — ffmpeg, 모델 다운로드, HF 토큰 설정."""

import logging
import os
import threading
from typing import Optional

import customtkinter as ctk

from src.utils.config import AppConfig
from src.gui import fonts
from src.utils.dependency import (
    DependencyStatus,
    is_ffmpeg_available,
    get_ffmpeg_version,
    download_ffmpeg,
    is_whisper_model_cached,
    is_diarize_model_cached,
    download_whisper_model,
    download_diarize_model,
    delete_ffmpeg,
    delete_whisper_model,
    delete_diarize_model,
    get_ffmpeg_size,
    get_whisper_model_size,
    get_diarize_model_size,
    get_ffmpeg_dir,
    format_size,
)

logger = logging.getLogger(__name__)


class SetupWizard(ctk.CTkToplevel):
    """의존성 관리 다이얼로그."""

    def __init__(self, master, config: AppConfig, **kwargs):
        super().__init__(master, **kwargs)
        self.title("의존성 관리")
        self.geometry("580x650")
        self.resizable(False, False)
        self._config = config
        self._downloading = False

        self.grid_columnconfigure(0, weight=1)

        self._build_ui()
        self._refresh_status()
        self.grab_set()

    def _build_ui(self):
        # 제목
        title = ctk.CTkLabel(
            self,
            text="의존성 관리",
            font=fonts.heading_font(),
        )
        title.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")

        desc = ctk.CTkLabel(
            self,
            text="프로그램 실행에 필요한 외부 도구와 모델을 관리합니다.",
            font=fonts.small_font(),
            text_color="gray60",
        )
        desc.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        # ── ffmpeg 섹션 ──
        self._ffmpeg_frame = self._create_section(
            row=2,
            title="ffmpeg",
            desc="오디오 변환에 필요 (필수)",
        )
        self._ffmpeg_status = ctk.CTkLabel(
            self._ffmpeg_frame, text="확인 중...",
            font=fonts.small_font(),
        )
        self._ffmpeg_status.grid(row=0, column=1, padx=10, sticky="w")

        self._ffmpeg_btn = ctk.CTkButton(
            self._ffmpeg_frame, text="다운로드", width=90,
            command=self._on_download_ffmpeg,
        )
        self._ffmpeg_btn.grid(row=0, column=2, padx=(5, 0))

        self._ffmpeg_del_btn = ctk.CTkButton(
            self._ffmpeg_frame, text="삭제", width=60,
            fg_color="gray40", hover_color="red",
            command=self._on_delete_ffmpeg,
        )
        self._ffmpeg_del_btn.grid(row=0, column=3, padx=(5, 10))

        self._ffmpeg_progress = ctk.CTkProgressBar(self._ffmpeg_frame, width=300)
        self._ffmpeg_progress.grid(row=1, column=0, columnspan=4, padx=10, pady=(5, 0), sticky="ew")
        self._ffmpeg_progress.set(0)
        self._ffmpeg_progress.grid_remove()

        self._ffmpeg_progress_label = ctk.CTkLabel(
            self._ffmpeg_frame, text="",
            font=fonts.small_font(), text_color="gray60",
        )
        self._ffmpeg_progress_label.grid(row=2, column=0, columnspan=4, padx=10, sticky="w")
        self._ffmpeg_progress_label.grid_remove()

        self._ffmpeg_info_label = ctk.CTkLabel(
            self._ffmpeg_frame, text="",
            font=fonts.small_font(), text_color="gray50",
        )
        self._ffmpeg_info_label.grid(row=3, column=0, columnspan=4, padx=10, pady=(0, 2), sticky="w")

        # ── Whisper 모델 섹션 ──
        self._whisper_frame = self._create_section(
            row=3,
            title="Whisper 모델 (large-v3)",
            desc="음성 인식에 사용 (첫 실행 시 자동 다운로드됨)",
        )
        self._whisper_status = ctk.CTkLabel(
            self._whisper_frame, text="확인 중...",
            font=fonts.small_font(),
        )
        self._whisper_status.grid(row=0, column=1, padx=10, sticky="w")

        self._whisper_btn = ctk.CTkButton(
            self._whisper_frame, text="다운로드", width=90,
            command=self._on_download_whisper,
        )
        self._whisper_btn.grid(row=0, column=2, padx=(5, 0))

        self._whisper_del_btn = ctk.CTkButton(
            self._whisper_frame, text="삭제", width=60,
            fg_color="gray40", hover_color="red",
            command=self._on_delete_whisper,
        )
        self._whisper_del_btn.grid(row=0, column=3, padx=(5, 10))

        self._whisper_progress = ctk.CTkProgressBar(self._whisper_frame, width=300, mode="indeterminate")
        self._whisper_progress.grid(row=1, column=0, columnspan=4, padx=10, pady=(5, 0), sticky="ew")
        self._whisper_progress.grid_remove()

        self._whisper_progress_label = ctk.CTkLabel(
            self._whisper_frame, text="",
            font=fonts.small_font(), text_color="gray60",
        )
        self._whisper_progress_label.grid(row=2, column=0, columnspan=4, padx=10, sticky="w")
        self._whisper_progress_label.grid_remove()

        self._whisper_info_label = ctk.CTkLabel(
            self._whisper_frame, text="",
            font=fonts.small_font(), text_color="gray50",
        )
        self._whisper_info_label.grid(row=3, column=0, columnspan=4, padx=10, pady=(0, 2), sticky="w")

        # ── 화자 분리 모델 섹션 ──
        self._diarize_frame = self._create_section(
            row=4,
            title="화자 분리 모델 (pyannote 3.1)",
            desc="화자 분리에 사용 (HF 토큰 필요)",
        )
        self._diarize_status = ctk.CTkLabel(
            self._diarize_frame, text="확인 중...",
            font=fonts.small_font(),
        )
        self._diarize_status.grid(row=0, column=1, padx=10, sticky="w")

        self._diarize_btn = ctk.CTkButton(
            self._diarize_frame, text="다운로드", width=90,
            command=self._on_download_diarize,
        )
        self._diarize_btn.grid(row=0, column=2, padx=(5, 0))

        self._diarize_del_btn = ctk.CTkButton(
            self._diarize_frame, text="삭제", width=60,
            fg_color="gray40", hover_color="red",
            command=self._on_delete_diarize,
        )
        self._diarize_del_btn.grid(row=0, column=3, padx=(5, 10))

        self._diarize_progress = ctk.CTkProgressBar(self._diarize_frame, width=300, mode="indeterminate")
        self._diarize_progress.grid(row=1, column=0, columnspan=4, padx=10, pady=(5, 0), sticky="ew")
        self._diarize_progress.grid_remove()

        self._diarize_progress_label = ctk.CTkLabel(
            self._diarize_frame, text="",
            font=fonts.small_font(), text_color="gray60",
        )
        self._diarize_progress_label.grid(row=2, column=0, columnspan=4, padx=10, sticky="w")
        self._diarize_progress_label.grid_remove()

        self._diarize_info_label = ctk.CTkLabel(
            self._diarize_frame, text="",
            font=fonts.small_font(), text_color="gray50",
        )
        self._diarize_info_label.grid(row=3, column=0, columnspan=4, padx=10, pady=(0, 2), sticky="w")

        # ── HF 토큰 섹션 ──
        hf_frame = ctk.CTkFrame(self)
        hf_frame.grid(row=5, column=0, padx=20, pady=(10, 5), sticky="ew")
        hf_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hf_frame, text="HuggingFace 토큰",
            font=fonts.body_bold_font(),
        ).grid(row=0, column=0, padx=10, pady=(10, 2), sticky="w", columnspan=3)

        ctk.CTkLabel(
            hf_frame,
            text="화자 분리 모델 다운로드에 필요합니다. huggingface.co/settings/tokens 에서 발급",
            font=fonts.small_font(),
            text_color="gray60",
        ).grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w", columnspan=3)

        self._hf_token_entry = ctk.CTkEntry(
            hf_frame,
            placeholder_text="hf_...",
            show="*",
        )
        self._hf_token_entry.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")

        # 기존 토큰이 있으면 마스킹 표시
        if self._config.hf_token:
            self._hf_token_entry.insert(0, self._config.hf_token)

        self._hf_save_btn = ctk.CTkButton(
            hf_frame, text="저장", width=70,
            command=self._on_save_hf_token,
        )
        self._hf_save_btn.grid(row=2, column=2, padx=(5, 10), pady=(0, 5))

        # 환경변수 감지 안내
        self._hf_env_label = ctk.CTkLabel(
            hf_frame, text="",
            font=fonts.small_font(), text_color="gray60",
        )
        self._hf_env_label.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="w", columnspan=3)

        env_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        if env_token:
            self._hf_env_label.configure(
                text=f"환경변수에서 토큰 감지됨 (HF_TOKEN={env_token[:10]}...)",
                text_color="green",
            )

        # ── 하단 버튼 ──
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=6, column=0, padx=20, pady=(10, 15), sticky="e")

        ctk.CTkButton(
            btn_frame, text="닫기", width=80,
            fg_color="gray40",
            command=self._on_close,
        ).pack(side="right")

    def _create_section(self, row: int, title: str, desc: str) -> ctk.CTkFrame:
        """의존성 항목 섹션 프레임 생성."""
        frame = ctk.CTkFrame(self)
        frame.grid(row=row, column=0, padx=20, pady=(5, 5), sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame, text=title,
            font=fonts.body_bold_font(),
        ).grid(row=0, column=0, padx=10, pady=(8, 2), sticky="w")

        ctk.CTkLabel(
            frame, text=desc,
            font=fonts.small_font(), text_color="gray60",
        ).grid(row=4, column=0, columnspan=4, padx=10, pady=(2, 8), sticky="w")

        return frame

    def _refresh_status(self):
        """모든 의존성 상태 갱신."""
        # ffmpeg
        ffmpeg_installed = is_ffmpeg_available()
        if ffmpeg_installed:
            version = get_ffmpeg_version()
            ver_text = f" (v{version})" if version else ""
            size = get_ffmpeg_size()
            size_text = f" ({format_size(size)})" if size > 0 else ""
            self._ffmpeg_status.configure(text=f"설치됨{ver_text}{size_text}", text_color="green")
            self._ffmpeg_btn.configure(text="재설치")
            self._ffmpeg_del_btn.configure(state="normal")
            self._ffmpeg_info_label.configure(text=f"경로: {get_ffmpeg_dir()}")
        else:
            self._ffmpeg_status.configure(text="미설치", text_color="red")
            self._ffmpeg_btn.configure(text="다운로드")
            self._ffmpeg_del_btn.configure(state="disabled")
            self._ffmpeg_info_label.configure(text="")

        # Whisper 모델
        whisper_cached = is_whisper_model_cached()
        if whisper_cached:
            size = get_whisper_model_size()
            size_text = f" ({format_size(size)})" if size > 0 else ""
            self._whisper_status.configure(text=f"캐시됨{size_text}", text_color="green")
            self._whisper_del_btn.configure(state="normal")
            self._whisper_info_label.configure(text="경로: ~/.cache/huggingface/hub/models--Systran--faster-whisper-large-v3/")
        else:
            self._whisper_status.configure(text="미설치", text_color="orange")
            self._whisper_del_btn.configure(state="disabled")
            self._whisper_info_label.configure(text="")

        # 화자 분리 모델
        hf_token = self._get_hf_token()
        diarize_cached = is_diarize_model_cached()
        if diarize_cached:
            size = get_diarize_model_size()
            size_text = f" ({format_size(size)})" if size > 0 else ""
            self._diarize_status.configure(text=f"캐시됨{size_text}", text_color="green")
            self._diarize_del_btn.configure(state="normal")
            self._diarize_info_label.configure(text="경로: ~/.cache/huggingface/hub/models--pyannote--speaker-diarization-3.1/")
        elif not hf_token:
            self._diarize_status.configure(text="토큰 필요", text_color="orange")
            self._diarize_btn.configure(state="disabled")
            self._diarize_del_btn.configure(state="disabled")
            self._diarize_info_label.configure(text="")
        else:
            self._diarize_status.configure(text="미설치", text_color="orange")
            self._diarize_btn.configure(state="normal")
            self._diarize_del_btn.configure(state="disabled")
            self._diarize_info_label.configure(text="")

    def _get_hf_token(self) -> str:
        """현재 사용 가능한 HF 토큰 반환."""
        return self._config.resolve_hf_token()

    # ── ffmpeg 다운로드 ──

    def _on_download_ffmpeg(self):
        if self._downloading:
            return
        self._downloading = True
        self._ffmpeg_btn.configure(state="disabled")
        self._ffmpeg_progress.grid()
        self._ffmpeg_progress_label.grid()
        self._ffmpeg_progress.set(0)

        # 재설치인 경우 기존 파일 삭제
        if is_ffmpeg_available():
            from src.utils.paths import get_app_data_dir
            ffmpeg_dir = get_app_data_dir() / "ffmpeg"
            for f in ["ffmpeg.exe", "ffprobe.exe"]:
                fp = ffmpeg_dir / f
                if fp.exists():
                    try:
                        fp.unlink()
                    except OSError:
                        pass

        def callback(ratio, msg):
            self.after(0, self._update_ffmpeg_progress, ratio, msg)

        def task():
            try:
                download_ffmpeg(callback)
                self.after(0, self._on_ffmpeg_done, True, "")
            except Exception as e:
                self.after(0, self._on_ffmpeg_done, False, str(e))

        threading.Thread(target=task, daemon=True).start()

    def _update_ffmpeg_progress(self, ratio: float, msg: str):
        self._ffmpeg_progress.set(ratio)
        self._ffmpeg_progress_label.configure(text=msg)

    def _on_ffmpeg_done(self, success: bool, error: str):
        self._downloading = False
        self._ffmpeg_btn.configure(state="normal")
        if success:
            self._ffmpeg_progress_label.configure(text="설치 완료!", text_color="green")
        else:
            self._ffmpeg_progress_label.configure(text=f"실패: {error}", text_color="red")
        self._refresh_status()

    # ── Whisper 모델 다운로드 ──

    def _on_download_whisper(self):
        if self._downloading:
            return
        self._downloading = True
        self._whisper_btn.configure(state="disabled")
        self._whisper_progress.grid()
        self._whisper_progress_label.grid()
        self._whisper_progress.start()

        def callback(ratio, msg):
            self.after(0, self._update_whisper_progress, msg)

        def task():
            try:
                ok = download_whisper_model(progress_callback=callback)
                self.after(0, self._on_whisper_done, ok, "")
            except Exception as e:
                self.after(0, self._on_whisper_done, False, str(e))

        threading.Thread(target=task, daemon=True).start()

    def _update_whisper_progress(self, msg: str):
        self._whisper_progress_label.configure(text=msg)

    def _on_whisper_done(self, success: bool, error: str):
        self._downloading = False
        self._whisper_btn.configure(state="normal")
        self._whisper_progress.stop()
        if success:
            self._whisper_progress.configure(mode="determinate")
            self._whisper_progress.set(1.0)
            self._whisper_progress_label.configure(text="다운로드 완료!", text_color="green")
        else:
            self._whisper_progress.configure(mode="determinate")
            self._whisper_progress.set(0)
            self._whisper_progress_label.configure(text=f"실패: {error}", text_color="red")
        self._refresh_status()

    # ── 화자 분리 모델 다운로드 ──

    def _on_download_diarize(self):
        if self._downloading:
            return

        hf_token = self._get_hf_token()
        if not hf_token:
            self._diarize_progress_label.grid()
            self._diarize_progress_label.configure(
                text="HF 토큰을 먼저 입력해주세요.", text_color="orange",
            )
            return

        self._downloading = True
        self._diarize_btn.configure(state="disabled")
        self._diarize_progress.grid()
        self._diarize_progress_label.grid()
        self._diarize_progress.start()

        def callback(ratio, msg):
            self.after(0, self._update_diarize_progress, msg)

        def task():
            try:
                ok = download_diarize_model(hf_token, callback)
                self.after(0, self._on_diarize_done, ok, "")
            except Exception as e:
                self.after(0, self._on_diarize_done, False, str(e))

        threading.Thread(target=task, daemon=True).start()

    def _update_diarize_progress(self, msg: str):
        self._diarize_progress_label.configure(text=msg)

    def _on_diarize_done(self, success: bool, error: str):
        self._downloading = False
        self._diarize_btn.configure(state="normal")
        self._diarize_progress.stop()
        if success:
            self._diarize_progress.configure(mode="determinate")
            self._diarize_progress.set(1.0)
            self._diarize_progress_label.configure(text="다운로드 완료!", text_color="green")
        else:
            self._diarize_progress.configure(mode="determinate")
            self._diarize_progress.set(0)
            self._diarize_progress_label.configure(text=f"실패: {error}", text_color="red")
        self._refresh_status()

    # ── 삭제 핸들러 ──

    def _confirm_delete(self, name: str, size: int, on_confirm):
        """삭제 확인 다이얼로그."""
        confirm = ctk.CTkToplevel(self)
        confirm.title("삭제 확인")
        confirm.geometry("380x140")
        confirm.resizable(False, False)

        size_text = format_size(size) if size > 0 else "알 수 없음"
        ctk.CTkLabel(
            confirm,
            text=f"{name}을(를) 정말 삭제하시겠습니까?\n({size_text} 해제됨)",
            font=fonts.body_font(),
        ).pack(pady=15)

        btn_frame = ctk.CTkFrame(confirm, fg_color="transparent")
        btn_frame.pack(pady=5)

        def do_delete():
            confirm.destroy()
            on_confirm()

        ctk.CTkButton(
            btn_frame, text="삭제", width=80,
            fg_color="red", hover_color="darkred",
            command=do_delete,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="취소", width=80,
            fg_color="gray40",
            command=confirm.destroy,
        ).pack(side="left", padx=5)

        confirm.grab_set()

    def _on_delete_ffmpeg(self):
        if self._downloading:
            return
        size = get_ffmpeg_size()
        self._confirm_delete("ffmpeg", size, self._do_delete_ffmpeg)

    def _do_delete_ffmpeg(self):
        try:
            delete_ffmpeg()
            logger.info("ffmpeg 삭제 완료")
        except Exception as e:
            logger.error(f"ffmpeg 삭제 실패: {e}")
        self._refresh_status()

    def _on_delete_whisper(self):
        if self._downloading:
            return
        size = get_whisper_model_size()
        self._confirm_delete("Whisper 모델", size, self._do_delete_whisper)

    def _do_delete_whisper(self):
        try:
            delete_whisper_model()
            logger.info("Whisper 모델 삭제 완료")
        except Exception as e:
            logger.error(f"Whisper 모델 삭제 실패: {e}")
        self._refresh_status()

    def _on_delete_diarize(self):
        if self._downloading:
            return
        size = get_diarize_model_size()
        self._confirm_delete("화자 분리 모델", size, self._do_delete_diarize)

    def _do_delete_diarize(self):
        try:
            delete_diarize_model()
            logger.info("화자 분리 모델 삭제 완료")
        except Exception as e:
            logger.error(f"화자 분리 모델 삭제 실패: {e}")
        self._refresh_status()

    # ── HF 토큰 저장 ──

    def _on_save_hf_token(self):
        token = self._hf_token_entry.get().strip()
        self._config.hf_token = token
        self._config.save()
        logger.info("HF 토큰 저장됨")

        # 화자 분리 모델 버튼 활성화 갱신
        self._refresh_status()

        # 저장 완료 피드백
        self._hf_save_btn.configure(text="저장됨!", fg_color="green")
        self.after(1500, lambda: self._hf_save_btn.configure(text="저장", fg_color=None))

    # ── 닫기 ──

    def _on_close(self):
        if self._downloading:
            # 다운로드 중이면 확인
            confirm = ctk.CTkToplevel(self)
            confirm.title("확인")
            confirm.geometry("350x130")
            confirm.resizable(False, False)

            ctk.CTkLabel(
                confirm,
                text="다운로드가 진행 중입니다.\n정말 닫으시겠습니까?",
                font=fonts.body_font(),
            ).pack(pady=15)

            btn_frame = ctk.CTkFrame(confirm, fg_color="transparent")
            btn_frame.pack(pady=5)

            ctk.CTkButton(
                btn_frame, text="닫기", width=80,
                fg_color="red", hover_color="darkred",
                command=lambda: (confirm.destroy(), self.destroy()),
            ).pack(side="left", padx=5)

            ctk.CTkButton(
                btn_frame, text="취소", width=80,
                fg_color="gray40",
                command=confirm.destroy,
            ).pack(side="left", padx=5)

            confirm.grab_set()
            return

        self.destroy()

"""옵션 설정 패널 컴포넌트."""

import customtkinter as ctk
from typing import Optional

from src.utils.config import AppConfig
from src.gui import fonts


class OptionsPanelFrame(ctk.CTkFrame):
    """처리 옵션 설정 패널."""

    def __init__(self, master, config: Optional[AppConfig] = None, **kwargs):
        super().__init__(master, **kwargs)
        self._config = config or AppConfig()
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # 제목
        title = ctk.CTkLabel(
            self,
            text="옵션 설정",
            font=fonts.body_bold_font(),
        )
        title.grid(row=0, column=0, columnspan=4, padx=10, pady=(10, 5), sticky="w")

        # 언어 선택
        lang_label = ctk.CTkLabel(self, text="언어:")
        lang_label.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")

        self.language_var = ctk.StringVar(value=self._config.language)
        self.language_menu = ctk.CTkOptionMenu(
            self,
            variable=self.language_var,
            values=["auto", "ko", "en", "ja", "zh"],
            width=120,
        )
        self.language_menu.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # 화자 수
        speaker_label = ctk.CTkLabel(self, text="화자 수:")
        speaker_label.grid(row=1, column=2, padx=(10, 5), pady=5, sticky="w")

        self.speakers_var = ctk.StringVar(
            value=str(self._config.num_speakers) if self._config.num_speakers else "자동"
        )
        self.speakers_menu = ctk.CTkOptionMenu(
            self,
            variable=self.speakers_var,
            values=["자동", "2", "3", "4", "5", "6"],
            width=100,
        )
        self.speakers_menu.grid(row=1, column=3, padx=(5, 10), pady=5, sticky="w")

        # 출력 포맷
        format_label = ctk.CTkLabel(self, text="출력 포맷:")
        format_label.grid(row=2, column=0, padx=(10, 5), pady=5, sticky="w")

        self.format_var = ctk.StringVar(value=self._config.output_format)
        self.format_menu = ctk.CTkOptionMenu(
            self,
            variable=self.format_var,
            values=["txt", "srt", "json"],
            width=120,
        )
        self.format_menu.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # 화자 분리 체크박스
        self.diarize_var = ctk.BooleanVar(value=True)
        self.diarize_check = ctk.CTkCheckBox(
            self,
            text="화자 분리",
            variable=self.diarize_var,
        )
        self.diarize_check.grid(row=2, column=2, padx=(10, 5), pady=5, sticky="w")

        # VAD 체크박스
        self.vad_var = ctk.BooleanVar(value=True)
        self.vad_check = ctk.CTkCheckBox(
            self,
            text="VAD 필터",
            variable=self.vad_var,
        )
        self.vad_check.grid(row=2, column=3, padx=(5, 10), pady=5, sticky="w")

    def get_language(self) -> str:
        return self.language_var.get()

    def get_num_speakers(self) -> Optional[int]:
        val = self.speakers_var.get()
        if val == "자동":
            return None
        return int(val)

    def get_output_format(self) -> str:
        return self.format_var.get()

    def is_diarization_enabled(self) -> bool:
        return self.diarize_var.get()

    def is_vad_enabled(self) -> bool:
        return self.vad_var.get()

    def set_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.language_menu.configure(state=state)
        self.speakers_menu.configure(state=state)
        self.format_menu.configure(state=state)
        self.diarize_check.configure(state=state)
        self.vad_check.configure(state=state)

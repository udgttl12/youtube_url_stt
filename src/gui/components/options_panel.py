"""옵션 설정 패널 컴포넌트."""

import customtkinter as ctk
from typing import Optional

from src.utils.config import AppConfig
from src.utils.device import DeviceConfig, WHISPER_MODELS
from src.gui import fonts


class OptionsPanelFrame(ctk.CTkFrame):
    """처리 옵션 설정 패널."""

    LANG_DISPLAY = {
        "auto": "자동 감지",
        "ko": "한국어",
        "en": "영어",
        "ja": "일본어",
        "zh": "중국어",
    }
    LANG_CODE = {v: k for k, v in LANG_DISPLAY.items()}

    MODEL_DISPLAY_VALUES = ["자동"] + WHISPER_MODELS
    BEAM_DISPLAY_VALUES = ["자동", "1", "2", "3", "5"]

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
        lang_label = ctk.CTkLabel(self, text="언어:", font=fonts.body_font())
        lang_label.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")

        lang_display = self.LANG_DISPLAY.get(self._config.language, "자동 감지")
        self.language_var = ctk.StringVar(value=lang_display)
        self.language_menu = ctk.CTkOptionMenu(
            self,
            variable=self.language_var,
            values=list(self.LANG_DISPLAY.values()),
            width=120,
            font=fonts.body_font(),
            dropdown_font=fonts.body_font(),
        )
        self.language_menu.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # 화자 수
        speaker_label = ctk.CTkLabel(self, text="화자 수:", font=fonts.body_font())
        speaker_label.grid(row=1, column=2, padx=(10, 5), pady=5, sticky="w")

        self.speakers_var = ctk.StringVar(
            value=str(self._config.num_speakers) if self._config.num_speakers else "자동"
        )
        self.speakers_menu = ctk.CTkOptionMenu(
            self,
            variable=self.speakers_var,
            values=["자동", "2", "3", "4", "5", "6"],
            width=100,
            font=fonts.body_font(),
            dropdown_font=fonts.body_font(),
        )
        self.speakers_menu.grid(row=1, column=3, padx=(5, 10), pady=5, sticky="w")

        # 출력 포맷
        format_label = ctk.CTkLabel(self, text="출력 포맷:", font=fonts.body_font())
        format_label.grid(row=2, column=0, padx=(10, 5), pady=5, sticky="w")

        self.format_var = ctk.StringVar(value=self._config.output_format)
        self.format_menu = ctk.CTkOptionMenu(
            self,
            variable=self.format_var,
            values=["txt", "srt", "json"],
            width=120,
            font=fonts.body_font(),
            dropdown_font=fonts.body_font(),
        )
        self.format_menu.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # 화자 분리 체크박스
        self.diarize_var = ctk.BooleanVar(value=True)
        self.diarize_check = ctk.CTkCheckBox(
            self,
            text="화자 분리",
            variable=self.diarize_var,
            font=fonts.body_font(),
        )
        self.diarize_check.grid(row=2, column=2, padx=(10, 5), pady=5, sticky="w")

        # VAD 체크박스
        self.vad_var = ctk.BooleanVar(value=True)
        self.vad_check = ctk.CTkCheckBox(
            self,
            text="VAD 필터",
            variable=self.vad_var,
            font=fonts.body_font(),
        )
        self.vad_check.grid(row=2, column=3, padx=(5, 10), pady=5, sticky="w")

        # 저사양 모드 체크박스
        self.low_power_var = ctk.BooleanVar(value=False)
        self.low_power_check = ctk.CTkCheckBox(
            self,
            text="저사양 모드",
            variable=self.low_power_var,
            font=fonts.body_font(),
        )
        self.low_power_check.grid(row=3, column=0, padx=(10, 5), pady=(5, 10), sticky="w")

        # 고급 옵션: Whisper 모델 선택
        model_label = ctk.CTkLabel(self, text="Whisper 모델:", font=fonts.body_font())
        model_label.grid(row=3, column=1, padx=(10, 5), pady=(5, 10), sticky="e")

        self.model_var = ctk.StringVar(value="자동")
        self.model_menu = ctk.CTkOptionMenu(
            self,
            variable=self.model_var,
            values=self.MODEL_DISPLAY_VALUES,
            width=150,
            font=fonts.body_font(),
            dropdown_font=fonts.body_font(),
        )
        self.model_menu.grid(row=3, column=2, padx=5, pady=(5, 10), sticky="w")

        # 추천 모델 표시 라벨
        self.model_hint_label = ctk.CTkLabel(
            self,
            text="",
            font=fonts.small_font(),
            text_color="gray60",
        )
        self.model_hint_label.grid(row=3, column=3, padx=(5, 10), pady=(5, 10), sticky="w")

        # Beam Size 선택
        beam_label = ctk.CTkLabel(self, text="Beam Size:", font=fonts.body_font())
        beam_label.grid(row=4, column=0, padx=(10, 5), pady=(0, 10), sticky="w")

        self.beam_var = ctk.StringVar(value="자동")
        self.beam_menu = ctk.CTkOptionMenu(
            self,
            variable=self.beam_var,
            values=self.BEAM_DISPLAY_VALUES,
            width=100,
            font=fonts.body_font(),
            dropdown_font=fonts.body_font(),
        )
        self.beam_menu.grid(row=4, column=1, padx=5, pady=(0, 10), sticky="w")

        # Beam Size 힌트
        self.beam_hint_label = ctk.CTkLabel(
            self,
            text="",
            font=fonts.small_font(),
            text_color="gray60",
        )
        self.beam_hint_label.grid(row=4, column=2, padx=5, pady=(0, 10), sticky="w")

    def get_language(self) -> str:
        display = self.language_var.get()
        return self.LANG_CODE.get(display, "auto")

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

    def is_low_power_enabled(self) -> bool:
        return self.low_power_var.get()

    def get_whisper_model(self) -> str:
        """선택된 Whisper 모델 반환. '자동'이면 빈 문자열."""
        val = self.model_var.get()
        if val == "자동":
            return ""
        return val

    def get_beam_size(self) -> int:
        """선택된 beam size 반환. '자동'이면 0."""
        val = self.beam_var.get()
        if val == "자동":
            return 0
        return int(val)

    def update_device_info(self, device_config: DeviceConfig):
        """디바이스 감지 후 추천 모델/beam_size 힌트 업데이트."""
        self.model_hint_label.configure(
            text=f"(추천: {device_config.whisper_model})"
        )
        self.beam_hint_label.configure(
            text=f"(추천: {device_config.recommended_beam_size})"
        )

    def set_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.language_menu.configure(state=state)
        self.speakers_menu.configure(state=state)
        self.format_menu.configure(state=state)
        self.diarize_check.configure(state=state)
        self.vad_check.configure(state=state)
        self.low_power_check.configure(state=state)
        self.model_menu.configure(state=state)
        self.beam_menu.configure(state=state)

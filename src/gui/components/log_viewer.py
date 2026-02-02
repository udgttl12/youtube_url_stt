"""로그 뷰어 컴포넌트."""

import customtkinter as ctk
from typing import Optional

from src.gui import fonts


class LogViewerFrame(ctk.CTkFrame):
    """실시간 로그 출력 프레임."""

    MAX_LINES = 500

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._line_count = 0
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 헤더
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header_frame,
            text="로그",
            font=fonts.body_bold_font(),
        )
        title.grid(row=0, column=0, sticky="w")

        clear_btn = ctk.CTkButton(
            header_frame,
            text="지우기",
            width=60,
            height=28,
            font=fonts.small_font(),
            command=self.clear,
        )
        clear_btn.grid(row=0, column=1, sticky="e")

        # 로그 텍스트 영역
        self.log_text = ctk.CTkTextbox(
            self,
            font=fonts.mono_font(),
            state="disabled",
            wrap="word",
        )
        self.log_text.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")

    def append_log(self, message: str):
        """로그 메시지 추가."""
        self.log_text.configure(state="normal")

        # 줄 수 제한
        if self._line_count >= self.MAX_LINES:
            self.log_text.delete("1.0", "2.0")
        else:
            self._line_count += 1

        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear(self):
        """로그 초기화."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._line_count = 0

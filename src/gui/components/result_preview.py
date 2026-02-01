"""결과 미리보기 및 저장 컴포넌트."""

import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog
from typing import Optional

from src.core.merger import MergedResult
from src.output.formatter import get_formatter
from src.gui import fonts


class ResultPreviewFrame(ctk.CTkFrame):
    """결과 미리보기 및 저장 프레임."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._result: Optional[MergedResult] = None
        self._current_format = "txt"
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
            text="결과 미리보기",
            font=fonts.body_bold_font(),
        )
        title.grid(row=0, column=0, sticky="w")

        # 포맷 전환 버튼들
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")

        self._format_buttons = {}
        for fmt in ["txt", "srt", "json"]:
            btn = ctk.CTkButton(
                btn_frame,
                text=fmt.upper(),
                width=50,
                height=28,
                command=lambda f=fmt: self._switch_format(f),
            )
            btn.pack(side="left", padx=2)
            self._format_buttons[fmt] = btn

        # 저장 버튼
        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="저장",
            width=70,
            height=28,
            fg_color="green",
            hover_color="darkgreen",
            command=self._save_file,
            state="disabled",
        )
        self.save_btn.pack(side="left", padx=(10, 0))

        # 미리보기 텍스트 영역
        self.preview_text = ctk.CTkTextbox(
            self,
            font=fonts.mono_font(),
            state="disabled",
            wrap="word",
        )
        self.preview_text.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")

    def set_result(self, result: MergedResult, format_type: str = "txt"):
        """결과를 설정하고 미리보기 표시."""
        self._result = result
        self._current_format = format_type
        self._render_preview()
        self.save_btn.configure(state="normal")

    def _switch_format(self, format_type: str):
        """포맷 전환."""
        self._current_format = format_type
        if self._result:
            self._render_preview()

    def _render_preview(self):
        """현재 포맷으로 미리보기 렌더링."""
        if not self._result:
            return

        try:
            formatter = get_formatter(self._current_format)
            content = formatter.format(self._result)

            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", content)
            self.preview_text.configure(state="disabled")

            # 활성 포맷 버튼 강조
            for fmt, btn in self._format_buttons.items():
                if fmt == self._current_format:
                    btn.configure(fg_color="#1f6aa5")
                else:
                    btn.configure(fg_color=("gray70", "gray30"))

        except Exception as e:
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", f"미리보기 오류: {e}")
            self.preview_text.configure(state="disabled")

    def _save_file(self):
        """결과를 파일로 저장."""
        if not self._result:
            return

        formatter = get_formatter(self._current_format)
        ext = formatter.extension

        file_path = filedialog.asksaveasfilename(
            title="결과 저장",
            defaultextension=ext,
            filetypes=[
                ("텍스트 파일", "*.txt"),
                ("SRT 자막", "*.srt"),
                ("JSON 파일", "*.json"),
                ("모든 파일", "*.*"),
            ],
            initialfile=f"transcript{ext}",
        )

        if file_path:
            try:
                output_path = Path(file_path)
                formatter.save(self._result, output_path)
                # 저장 성공 알림
                self.save_btn.configure(text="저장 완료!", fg_color="darkgreen")
                self.after(2000, lambda: self.save_btn.configure(
                    text="저장", fg_color="green"
                ))
            except Exception as e:
                self.save_btn.configure(text="저장 실패", fg_color="red")
                self.after(2000, lambda: self.save_btn.configure(
                    text="저장", fg_color="green"
                ))

    def clear(self):
        """미리보기 초기화."""
        self._result = None
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.configure(state="disabled")
        self.save_btn.configure(state="disabled")

"""URL 입력 컴포넌트."""

import customtkinter as ctk
from typing import Callable, Optional

from src.gui import fonts


class URLInputFrame(ctk.CTkFrame):
    """YouTube URL 입력 프레임."""

    def __init__(
        self,
        master,
        on_submit: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._on_submit = on_submit
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)

        # 라벨
        label = ctk.CTkLabel(
            self,
            text="YouTube URL:",
            font=fonts.subheading_font(),
        )
        label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        # URL 입력
        self.url_entry = ctk.CTkEntry(
            self,
            placeholder_text="https://www.youtube.com/watch?v=...",
            font=fonts.entry_font(),
            height=38,
        )
        self.url_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.url_entry.bind("<Return>", lambda e: self._submit())

    def _submit(self):
        url = self.get_url()
        if url and self._on_submit:
            self._on_submit(url)

    def get_url(self) -> str:
        return self.url_entry.get().strip()

    def set_url(self, url: str):
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, url)

    def set_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.url_entry.configure(state=state)

"""URL 입력 컴포넌트."""

import customtkinter as ctk
from typing import Callable, Optional


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
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        # URL 입력
        self.url_entry = ctk.CTkEntry(
            self,
            placeholder_text="https://www.youtube.com/watch?v=...",
            font=ctk.CTkFont(size=13),
            height=38,
        )
        self.url_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.url_entry.bind("<Return>", lambda e: self._submit())

        # 붙여넣기 버튼
        paste_btn = ctk.CTkButton(
            self,
            text="붙여넣기",
            width=80,
            height=38,
            command=self._paste,
        )
        paste_btn.grid(row=0, column=2, padx=(5, 10), pady=10)

    def _paste(self):
        """클립보드에서 URL 붙여넣기."""
        try:
            clipboard = self.clipboard_get()
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, clipboard.strip())
        except Exception:
            pass

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

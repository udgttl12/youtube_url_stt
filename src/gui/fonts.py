"""GUI 폰트 중앙 설정 — 한글 가독성 최적화."""

import customtkinter as ctk

# 기본 폰트: 맑은 고딕 (Windows 표준 한글 폰트)
FONT_FAMILY = "맑은 고딕"
# 고정폭 폰트: 로그/코드 영역용
MONO_FAMILY = "Consolas"


def title_font() -> ctk.CTkFont:
    """메인 타이틀 (20px bold)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold")


def heading_font() -> ctk.CTkFont:
    """섹션 제목 (15px bold)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold")


def subheading_font() -> ctk.CTkFont:
    """소제목 (14px bold)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")


def body_font() -> ctk.CTkFont:
    """본문 텍스트 (13px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=13)


def body_bold_font() -> ctk.CTkFont:
    """본문 강조 (13px bold)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")


def small_font() -> ctk.CTkFont:
    """보조 텍스트 (12px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=12)


def small_bold_font() -> ctk.CTkFont:
    """보조 강조 텍스트 (12px bold)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")


def button_font() -> ctk.CTkFont:
    """버튼 텍스트 (13px bold)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")


def button_large_font() -> ctk.CTkFont:
    """큰 버튼 텍스트 (15px bold)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold")


def entry_font() -> ctk.CTkFont:
    """입력 필드 (13px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=13)


def mono_font() -> ctk.CTkFont:
    """고정폭 텍스트 — 로그/코드 영역 (12px)."""
    return ctk.CTkFont(family=MONO_FAMILY, size=12)


def badge_font() -> ctk.CTkFont:
    """배지/인디케이터 (12px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=12)

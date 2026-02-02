"""GUI 폰트 중앙 설정 — 한글 가독성 최적화."""

import ctypes
import os
import sys

import customtkinter as ctk

# 기본 폰트: Pretendard (프로젝트 번들)
FONT_FAMILY = "Pretendard"
# 고정폭 폰트: 로그/코드 영역용
MONO_FAMILY = "Consolas"

# Pretendard TTF 폰트를 Windows GDI에 런타임 등록
_fonts_registered = False


def _register_pretendard():
    """프로젝트 fonts/ 디렉토리에서 Pretendard TTF를 시스템에 등록."""
    global _fonts_registered
    if _fonts_registered:
        return

    if sys.platform != "win32":
        _fonts_registered = True
        return

    # PyInstaller 번들 또는 개발 환경 경로
    if getattr(sys, "_MEIPASS", None):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    font_dir = os.path.join(base, "fonts", "Pretendard-1.3.9", "public", "static", "alternative")
    if not os.path.isdir(font_dir):
        _fonts_registered = True
        return

    gdi32 = ctypes.windll.gdi32
    for fname in os.listdir(font_dir):
        if fname.lower().endswith(".ttf"):
            font_path = os.path.join(font_dir, fname)
            gdi32.AddFontResourceW(font_path)

    _fonts_registered = True


_register_pretendard()


def title_font() -> ctk.CTkFont:
    """메인 타이틀 (20px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=20, weight="normal")


def heading_font() -> ctk.CTkFont:
    """섹션 제목 (15px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=15, weight="normal")


def subheading_font() -> ctk.CTkFont:
    """소제목 (14px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=14, weight="normal")


def body_font() -> ctk.CTkFont:
    """본문 텍스트 (13px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=13)


def body_bold_font() -> ctk.CTkFont:
    """본문 강조 (13px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=13, weight="normal")


def small_font() -> ctk.CTkFont:
    """보조 텍스트 (12px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=12)


def small_bold_font() -> ctk.CTkFont:
    """보조 강조 텍스트 (12px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=12, weight="normal")


def button_font() -> ctk.CTkFont:
    """버튼 텍스트 (13px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=13, weight="normal")


def button_large_font() -> ctk.CTkFont:
    """큰 버튼 텍스트 (15px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=15, weight="normal")


def entry_font() -> ctk.CTkFont:
    """입력 필드 (13px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=13)


def mono_font() -> ctk.CTkFont:
    """고정폭 텍스트 — 로그/코드 영역 (12px)."""
    return ctk.CTkFont(family=MONO_FAMILY, size=12)


def badge_font() -> ctk.CTkFont:
    """배지/인디케이터 (12px)."""
    return ctk.CTkFont(family=FONT_FAMILY, size=12)

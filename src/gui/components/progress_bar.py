"""진행률 표시 컴포넌트."""

import customtkinter as ctk
from typing import Optional

from src.core.pipeline import PipelineStage
from src.gui import fonts


# 각 단계별 전체 진행률 범위
STAGE_RANGES = {
    PipelineStage.INIT: (0.0, 0.02),
    PipelineStage.DOWNLOAD: (0.02, 0.15),
    PipelineStage.PREPROCESS: (0.15, 0.25),
    PipelineStage.DIARIZE: (0.25, 0.50),
    PipelineStage.TRANSCRIBE: (0.50, 0.90),
    PipelineStage.MERGE: (0.90, 0.95),
    PipelineStage.OUTPUT: (0.95, 1.00),
    PipelineStage.DONE: (1.0, 1.0),
    PipelineStage.ERROR: (0.0, 0.0),
}


class ProgressFrame(ctk.CTkFrame):
    """단계별 진행률 표시 프레임."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # 현재 단계 라벨
        self.stage_label = ctk.CTkLabel(
            self,
            text="대기 중",
            font=fonts.body_bold_font(),
        )
        self.stage_label.grid(row=0, column=0, padx=10, pady=(10, 2), sticky="w")

        # 상세 상태 라벨
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=fonts.small_font(),
            text_color="gray60",
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=(10, 2), sticky="e")

        # 전체 진행률 바
        self.progress_bar = ctk.CTkProgressBar(self, height=20)
        self.progress_bar.grid(row=1, column=0, padx=10, pady=(2, 5), sticky="ew")
        self.progress_bar.set(0)

        # 퍼센트 라벨
        self.percent_label = ctk.CTkLabel(
            self,
            text="0%",
            font=fonts.small_font(),
        )
        self.percent_label.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="e")

        # 단계 인디케이터
        self.stages_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stages_frame.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.stages_frame.grid_columnconfigure(
            tuple(range(6)), weight=1
        )

        self._stage_labels = {}
        stage_names = [
            ("다운로드", PipelineStage.DOWNLOAD),
            ("전처리", PipelineStage.PREPROCESS),
            ("화자분리", PipelineStage.DIARIZE),
            ("STT", PipelineStage.TRANSCRIBE),
            ("병합", PipelineStage.MERGE),
            ("출력", PipelineStage.OUTPUT),
        ]

        for i, (name, stage) in enumerate(stage_names):
            lbl = ctk.CTkLabel(
                self.stages_frame,
                text=f"  {name}  ",
                font=fonts.badge_font(),
                corner_radius=6,
                fg_color="gray25",
                text_color="gray60",
            )
            lbl.grid(row=0, column=i, padx=2, pady=2, sticky="ew")
            self._stage_labels[stage] = lbl

    def update_progress(self, stage: PipelineStage, stage_progress: float, message: str):
        """진행률 업데이트.

        Args:
            stage: 현재 파이프라인 단계
            stage_progress: 단계 내 진행률 (0.0~1.0)
            message: 상태 메시지
        """
        # 전체 진행률 계산
        start, end = STAGE_RANGES.get(stage, (0, 0))
        overall = start + (end - start) * min(stage_progress, 1.0)

        self.stage_label.configure(text=f"[{stage.value}]")
        self.status_label.configure(text=message)
        self.progress_bar.set(overall)
        self.percent_label.configure(text=f"{overall*100:.0f}%")

        # 단계 인디케이터 업데이트
        self._update_stage_indicators(stage)

    def _update_stage_indicators(self, current_stage: PipelineStage):
        """단계 인디케이터 색상 업데이트."""
        stage_order = [
            PipelineStage.DOWNLOAD,
            PipelineStage.PREPROCESS,
            PipelineStage.DIARIZE,
            PipelineStage.TRANSCRIBE,
            PipelineStage.MERGE,
            PipelineStage.OUTPUT,
        ]

        current_idx = -1
        for i, s in enumerate(stage_order):
            if s == current_stage:
                current_idx = i
                break

        for i, stage in enumerate(stage_order):
            lbl = self._stage_labels.get(stage)
            if lbl is None:
                continue

            if current_stage == PipelineStage.DONE:
                lbl.configure(fg_color="green", text_color="white")
            elif current_stage == PipelineStage.ERROR:
                if i <= current_idx:
                    lbl.configure(fg_color="red", text_color="white")
            elif i < current_idx:
                lbl.configure(fg_color="green", text_color="white")
            elif i == current_idx:
                lbl.configure(fg_color="#1f6aa5", text_color="white")
            else:
                lbl.configure(fg_color="gray25", text_color="gray60")

    def reset(self):
        """진행률 초기화."""
        self.stage_label.configure(text="대기 중")
        self.status_label.configure(text="")
        self.progress_bar.set(0)
        self.percent_label.configure(text="0%")
        for lbl in self._stage_labels.values():
            lbl.configure(fg_color="gray25", text_color="gray60")

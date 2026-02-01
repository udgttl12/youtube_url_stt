# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

YouTube 영상 URL로부터 음성을 추출하여 화자 분리(Speaker Diarization) + STT(Speech-to-Text)를 수행하는 Windows 로컬 프로그램. 완전 무료, 외부 API 미사용, GPU/CPU 자동 전환.

## 실행 명령어

```bash
# GUI 모드 (기본)
python main.py

# CLI 모드
python main.py --cli --url <YOUTUBE_URL> [--language ko] [--speakers 2] [--format txt] [--output result.txt] [--cpu] [--verbose]

# 의존성 사전 다운로드 (ffmpeg, Whisper, diarization 모델)
python main.py --setup [--hf-token TOKEN]

# venv 생성 (Python 3.12 필요 — 3.14는 onnxruntime 미지원)
py -3.12 -m venv venv

# 의존성 설치 (venv 활성화 후)
venv\Scripts\pip install -r requirements.txt

# GPU 사용 시 CUDA PyTorch 별도 설치 필요 (CPU 버전 대체)
venv\Scripts\pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu126

# PyInstaller 빌드 (exe 패키징) → dist/YouTubeSTT/
venv\Scripts\pip install pyinstaller
venv\Scripts\python -m PyInstaller build.spec -y
```

## 아키텍처

### 처리 파이프라인

`Pipeline` (src/core/pipeline.py)이 전체 흐름을 조율하며, 각 단계는 독립 모듈:

```
YouTubeDownloader → AudioPreprocessor → SpeakerDiarizer → Transcriber → ResultMerger → Formatter
```

1. **downloader.py** - yt-dlp로 오디오 추출 (WAV), 3회 재시도, URL 정규식 검증
2. **preprocessor.py** - 16kHz mono 변환, RMS 정규화(-20dB), 클리핑 방지(0.99 임계값)
3. **diarizer.py** - pyannote.audio 3.1 화자 분리. 모델 로딩 순서: ① `resources/pyannote/` 로컬 번들 → ② HuggingFace Hub 폴백
4. **transcriber.py** - faster-whisper (large-v3), 단어 단위 타임스탬프. `transcribe_full()`과 `transcribe_with_vad()` 두 모드
5. **merger.py** - 각 단어의 midpoint 시간을 화자 구간에 매핑하여 귀속
6. **src/output/** - 출력 포맷터 모듈 (txt/srt/json). main.py에서 `from src.output.formatter import get_formatter`로 참조

### GUI

customtkinter 기반 다크 모드. `src/gui/app.py`가 메인 윈도우, `src/gui/components/`에 URL 입력/옵션 패널/진행바/로그 뷰어/결과 미리보기. Pipeline은 별도 스레드에서 실행. 폰트 설정은 `src/gui/fonts.py`에서 중앙 관리 (맑은 고딕/Consolas).

`src/gui/setup_wizard.py`는 의존성 관리 다이얼로그로 ffmpeg/Whisper/Diarizer 모델의 다운로드·삭제·용량 표시를 탭 기반 UI로 제공.

### 디바이스 관리

`DeviceManager` (src/utils/device.py)가 CUDA 여부를 감지하여 자동 전환:
- GPU: cuda, float16, large-v3 모델
- CPU: cpu, int8, large-v3 모델

### 경로 탐색 규칙

**ffmpeg** (src/utils/paths.py `get_ffmpeg_path()`):
1. `resources/ffmpeg/ffmpeg.exe` (PyInstaller 번들)
2. `~/.youtube_stt/ffmpeg/ffmpeg.exe` (사용자 다운로드)
3. 시스템 PATH

**pyannote 모델** (src/utils/paths.py `get_pyannote_config_path()`):
- `resources/pyannote/`에 `.bin` 모델 파일이 있으면 `config.yaml`과 PLDA 더미 파일을 자동 생성
- 로컬 모델 로딩 시 `os.chdir()`로 CWD를 변경하여 config.yaml 내 상대경로 해석 (diarizer.py:62)

**HF 토큰 해석 우선순위** (AppConfig.resolve_hf_token):
1. CLI 인자 (`--hf-token`)
2. 환경변수 (`HF_TOKEN`, `HUGGING_FACE_HUB_TOKEN`)
3. 저장된 설정 (`~/.youtube_stt/config.json`)

### 설정/경로

- 설정 파일: `~/.youtube_stt/config.json` (AppConfig, src/utils/config.py)
- 모델 캐시: `~/.youtube_stt/models/`
- 임시 파일: `~/.youtube_stt/temp/` (Pipeline 완료 후 자동 정리)
- 출력 디렉토리: `~/.youtube_stt/output/`
- PyInstaller 번들 시 `sys._MEIPASS`가 base dir로 사용됨 (paths.py `get_base_dir()`)

## 핵심 설계 결정

- 화자 분리 실패 시 단일 화자 모드로 자동 폴백 (pipeline.py:124)
- HF 토큰이 없어도 diarization만 건너뛰고 STT는 정상 실행
- 병합(merger)은 단어 단위 midpoint 방식으로 화자 귀속 — 구간 단위가 아니라 단어 하나하나의 중간 시점을 화자 세그먼트에 매칭
- Pipeline은 취소(cancellation) 지원, `stage_callback(stage, progress, message)`으로 UI 진행률 업데이트. 각 모듈(downloader, preprocessor, diarizer, transcriber)에 `cancel_check` 콜백을 전달하여 단계 내부 블로킹 호출 중에도 취소 가능. `CancelledError`는 각 모듈의 `except Exception` catch-all보다 먼저 `except CancelledError: raise`로 투명 전파되어 모듈 실패가 아닌 취소로 올바르게 처리됨
- 커스텀 예외 계층: `YouTubeSTTError` → `DownloadError`, `PreprocessError`, `TranscribeError`, `DiarizeError`, `MergeError`, `ModelLoadError`, `FFmpegNotFoundError`, `DependencySetupError`, `CancelledError`
- 의존성 관리(src/utils/dependency.py)에서 ffmpeg는 Gyan/BtbN 두 소스에서 폴백 다운로드

## 향후 기능 (TODO)

- **URL 큐(Queue) 일괄 처리**: 여러 YouTube 링크를 목록으로 등록하고 순차적으로 자동 처리. 작업 진행 중에도 큐에 새 URL 추가 가능해야 함
- **시스템 트레이 지원**: 창 닫기 시 트레이로 최소화, 종료 확인 다이얼로그 제공

## 외부 요구사항

- **HuggingFace 토큰**: 화자 분리(pyannote.audio) 사용 시 필요. `pyannote/speaker-diarization-3.1`, `pyannote/segmentation-3.0` 모델에 사용 동의(Accept) 필수
- **ffmpeg**: `resources/ffmpeg/`에 번들, `~/.youtube_stt/ffmpeg/`에 자동 다운로드, 또는 시스템 PATH
- **PyTorch + CUDA**: GPU 가속 시 필요 (없으면 CPU 자동 전환)
- **Python 3.9+**

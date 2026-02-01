# YouTube 화자 분리 + STT

유튜브 영상 URL을 입력하면 화자를 분리하고 음성을 텍스트로 변환하는 로컬 프로그램.

## 사전 준비

### 1. Python 설치

Python 3.9 이상이 필요합니다. [python.org](https://www.python.org/downloads/)에서 다운로드하세요.

### 2. ffmpeg 설치

오디오 처리에 ffmpeg가 필요합니다. 아래 방법 중 하나를 선택하세요.

**방법 A) 시스템 PATH에 설치 (권장)**

[ffmpeg.org](https://ffmpeg.org/download.html)에서 Windows 빌드를 다운로드하고 `ffmpeg.exe`, `ffprobe.exe`를 시스템 PATH에 추가합니다.

```bash
# 설치 확인
ffmpeg -version
```

**방법 B) 프로젝트에 직접 배치**

`resources/ffmpeg/` 폴더에 `ffmpeg.exe`와 `ffprobe.exe`를 넣으면 자동으로 인식합니다.

### 3. HuggingFace 토큰 발급 (화자 분리용)

화자 분리 기능을 사용하려면 HuggingFace 토큰이 필요합니다.

1. [huggingface.co](https://huggingface.co/)에 가입
2. [토큰 페이지](https://huggingface.co/settings/tokens)에서 Access Token 생성 (Read 권한)
3. 아래 모델 페이지에 접속하여 **사용 동의(Accept)** 클릭:
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0

> 화자 분리 없이 STT만 사용하려면 토큰 없이도 실행 가능합니다 (`--no-diarize` 옵션).

### 4. 의존성 설치

```bash
pip install -r requirements.txt
```

GPU를 사용하려면 CUDA를 지원하는 PyTorch를 설치해야 합니다. [PyTorch 설치 가이드](https://pytorch.org/get-started/locally/)에서 본인 환경에 맞는 명령어를 확인하세요.

```bash
# 예시: CUDA 12.1 기준
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## 실행 방법

### GUI 모드

```bash
python main.py
```

1. URL 입력란에 유튜브 영상 주소 입력
2. 옵션 설정 (언어, 화자 수, 출력 포맷)
3. 최초 실행 시 HuggingFace 토큰 입력 다이얼로그가 나타남 (한 번 입력하면 저장됨)
4. 실행 버튼 클릭 후 진행 상태 확인
5. 완료 후 결과 미리보기 및 파일 저장

### CLI 모드

```bash
# 기본 사용
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID"

# 한국어 고정, 화자 2명, JSON 출력
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID" \
    --language ko --speakers 2 --format json --output result.json

# HuggingFace 토큰 직접 지정
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID" \
    --hf-token "hf_xxxxxxxxxxxx"

# 화자 분리 없이 STT만 실행
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID" --no-diarize

# CPU 강제 사용
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID" --cpu

# 상세 로그 출력
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID" --verbose
```

### CLI 옵션 목록

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--cli` | CLI 모드로 실행 | (GUI 모드) |
| `--url` | YouTube 영상 URL (CLI 필수) | - |
| `--language` | 언어 코드 (`auto`, `ko`, `en` 등) | `auto` |
| `--speakers` | 화자 수 (미지정 시 자동 감지) | 자동 |
| `--format` | 출력 포맷 (`txt`, `srt`, `json`) | `txt` |
| `--output`, `-o` | 출력 파일 경로 | stdout |
| `--hf-token` | HuggingFace 토큰 | 저장된 값 사용 |
| `--no-diarize` | 화자 분리 비활성화 | false |
| `--no-vad` | VAD 필터 비활성화 | false |
| `--cpu` | CPU 모드 강제 사용 | 자동 감지 |
| `--verbose`, `-v` | 상세 로그 출력 | false |

## 출력 포맷

### TXT (기본)

```
[00:00:02 - 00:00:07] SPEAKER_0
안녕하세요 오늘 회의 시작하겠습니다.

[00:00:07 - 00:00:12] SPEAKER_1
네, 자료 공유드리겠습니다.
```

### SRT (자막)

표준 자막 형식으로 출력됩니다. 영상 편집 도구나 미디어 플레이어에서 사용할 수 있습니다.

### JSON (구조화 데이터)

```json
{
  "metadata": {
    "num_speakers": 2,
    "language": "ko",
    "duration": 330.0
  },
  "segments": [
    {
      "speaker": "SPEAKER_0",
      "start": 2.0,
      "end": 7.5,
      "text": "안녕하세요 오늘 회의 시작하겠습니다."
    }
  ]
}
```

## 데이터 저장 위치

모든 앱 데이터는 `~/.youtube_stt/` 에 저장됩니다.

| 경로 | 용도 |
|------|------|
| `~/.youtube_stt/config.json` | 설정 (토큰, 언어, 포맷 등) |
| `~/.youtube_stt/models/` | 다운로드된 모델 캐시 |
| `~/.youtube_stt/temp/` | 처리 중 임시 파일 |
| `~/.youtube_stt/output/` | 기본 결과 출력 |

## exe 빌드

```bash
pyinstaller build.spec
```

빌드 결과는 `dist/YouTubeSTT/` 에 생성됩니다. 최초 실행 시 모델을 자동 다운로드하며 이후 캐시를 재사용합니다.

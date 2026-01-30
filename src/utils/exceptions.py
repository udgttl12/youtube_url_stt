"""커스텀 예외 클래스 정의."""


class YouTubeSTTError(Exception):
    """기본 예외 클래스."""
    pass


class DownloadError(YouTubeSTTError):
    """YouTube 다운로드 실패."""
    pass


class PreprocessError(YouTubeSTTError):
    """오디오 전처리 실패."""
    pass


class TranscribeError(YouTubeSTTError):
    """STT 변환 실패."""
    pass


class DiarizeError(YouTubeSTTError):
    """화자 분리 실패."""
    pass


class MergeError(YouTubeSTTError):
    """결과 병합 실패."""
    pass


class ModelLoadError(YouTubeSTTError):
    """모델 로드 실패."""
    pass


class FFmpegNotFoundError(YouTubeSTTError):
    """FFmpeg 바이너리를 찾을 수 없음."""
    pass

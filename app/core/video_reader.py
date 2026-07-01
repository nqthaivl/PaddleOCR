from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2


@dataclass(slots=True)
class VideoMetadata:
    path: str
    width: int
    height: int
    fps: float
    frame_count: int
    duration: float
    codec: str = "unknown"


class VideoReader:
    def __init__(self, path: str):
        self.path = str(path)
        self.capture = cv2.VideoCapture(self.path)
        if not self.capture.isOpened():
            raise RuntimeError(f"Không mở được video: {path}")
        self.metadata = self._read_metadata()

    def _read_metadata(self) -> VideoMetadata:
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(self.capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = frame_count / fps if fps > 0 else 0.0
        fourcc = int(self.capture.get(cv2.CAP_PROP_FOURCC) or 0)
        codec = "".join(chr((fourcc >> 8 * i) & 0xFF) for i in range(4)).strip() or "unknown"
        return VideoMetadata(
            path=self.path,
            width=width,
            height=height,
            fps=fps,
            frame_count=frame_count,
            duration=duration,
            codec=codec,
        )

    def read_at(self, timestamp: float):
        timestamp = max(0.0, min(timestamp, self.metadata.duration))
        self.capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
        ok, frame = self.capture.read()
        if not ok:
            return None
        return frame

    def close(self) -> None:
        self.capture.release()

    @staticmethod
    def default_output_path(video_path: str, extension: str = "srt") -> str:
        return str(Path(video_path).with_suffix(f".{extension.lower()}"))


from __future__ import annotations

import traceback

from PyQt6.QtCore import QThread, pyqtSignal

from app.core.frame_sampler import iter_timestamps
from app.core.ocr_engine import OcrEngine
from app.core.preprocess import Roi, preprocess_for_ocr
from app.core.subtitle_builder import SubtitleBuilder
from app.core.video_reader import VideoReader
from app.models.settings import AppSettings
from app.models.subtitle import OcrSample, SubtitleSegment


class OcrWorker(QThread):
    progress_changed = pyqtSignal(int)
    sample_ready = pyqtSignal(float, str, float)
    segments_ready = pyqtSignal(list)
    status_changed = pyqtSignal(str)
    failed = pyqtSignal(str)
    finished_ok = pyqtSignal()

    def __init__(self, video_path: str, roi: Roi, settings: AppSettings):
        super().__init__()
        self.video_path = video_path
        self.roi = roi
        self.settings = settings
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        reader: VideoReader | None = None
        try:
            self.status_changed.emit("Đang khởi tạo PaddleOCR...")
            engine = OcrEngine(
                language=self.settings.language,
                use_gpu=self.settings.runtime.use_gpu,
            )
            self.status_changed.emit(engine.runtime_probe.message)

            reader = VideoReader(self.video_path)
            duration = reader.metadata.duration
            timestamps = list(iter_timestamps(duration, self.settings.frame_step_seconds))
            total = max(1, len(timestamps))
            samples: list[OcrSample] = []

            for index, timestamp in enumerate(timestamps, start=1):
                if self._stop_requested:
                    self.status_changed.emit("Đã dừng theo yêu cầu người dùng.")
                    break

                frame = reader.read_at(timestamp)
                if frame is None:
                    continue
                crop = preprocess_for_ocr(frame, self.roi, self.settings.preprocess)
                lines = engine.recognize(crop)
                if lines:
                    text = " ".join(part for part, _ in lines).strip()
                    confidence = max(score for _, score in lines)
                    sample = OcrSample(timestamp, text, confidence)
                    samples.append(sample)
                    self.sample_ready.emit(timestamp, text, confidence)

                percent = int(index * 100 / total)
                self.progress_changed.emit(percent)
                self.status_changed.emit(f"OCR {index}/{total} khung hình")

            builder = SubtitleBuilder(
                self.settings.merge,
                self.settings.confidence_threshold,
                self.settings.frame_step_seconds,
            )
            segments = builder.build(samples)
            self.segments_ready.emit(segments)
            self.progress_changed.emit(100)
            self.finished_ok.emit()
        except Exception as exc:
            traceback.print_exc()
            details = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.failed.emit(details)
        finally:
            if reader:
                reader.close()




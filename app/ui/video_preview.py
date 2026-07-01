from __future__ import annotations

import cv2
from PyQt6.QtCore import QSize, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QStyle,
)

from app.core.video_reader import VideoReader
from app.ui.roi_selector import RoiSelector


class VideoPreview(QFrame):
    timestamp_changed = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.setObjectName("VideoPanel")
        self.reader: VideoReader | None = None
        self.current_frame = None
        self.duration = 0.0

        self.roi_selector = RoiSelector()
        self.meta_label = QLabel("Chưa mở video")
        self.meta_label.setObjectName("MetaLabel")
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setRange(0, 1000)
        self.timeline.valueChanged.connect(self._on_timeline)

        self.btn_fit_bottom = QPushButton("Chọn 25% phía dưới")
        self.btn_reset_roi = QPushButton("Đặt lại vùng")
        self.btn_preview_crop = QPushButton("Xem vùng cắt")
        self._apply_icons()
        self.btn_fit_bottom.clicked.connect(self.roi_selector.fit_bottom)
        self.btn_reset_roi.clicked.connect(self.roi_selector.reset_roi)

        button_row = QHBoxLayout()
        button_row.addWidget(self.btn_fit_bottom)
        button_row.addWidget(self.btn_reset_roi)
        button_row.addWidget(self.btn_preview_crop)
        button_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.roi_selector, 1)
        layout.addWidget(self.meta_label)
        layout.addWidget(self.timeline)
        layout.addLayout(button_row)

    def _apply_icons(self) -> None:
        icon_size = QSize(17, 17)
        icon_map = {
            self.btn_fit_bottom: QStyle.StandardPixmap.SP_ArrowDown,
            self.btn_reset_roi: QStyle.StandardPixmap.SP_BrowserReload,
            self.btn_preview_crop: QStyle.StandardPixmap.SP_FileDialogInfoView,
        }
        for button, standard_icon in icon_map.items():
            button.setIcon(self.style().standardIcon(standard_icon))
            button.setIconSize(icon_size)

    def load_video(self, path: str) -> None:
        if self.reader:
            self.reader.close()
        self.reader = VideoReader(path)
        meta = self.reader.metadata
        self.duration = meta.duration
        self.roi_selector.set_video_size(meta.width, meta.height)
        self.meta_label.setText(
            f"{meta.width}x{meta.height} | {meta.fps:.2f} FPS | "
            f"{meta.duration:.2f}s | codec {meta.codec}"
        )
        self.seek(0.0)

    def seek(self, timestamp: float) -> None:
        if not self.reader:
            return
        frame = self.reader.read_at(timestamp)
        if frame is None:
            return
        self.current_frame = frame
        self._show_frame(frame)
        if self.duration > 0:
            self.timeline.blockSignals(True)
            self.timeline.setValue(int(timestamp / self.duration * 1000))
            self.timeline.blockSignals(False)
        self.timestamp_changed.emit(timestamp)

    def current_roi(self) -> tuple[int, int, int, int]:
        return self.roi_selector.current_roi()

    def _on_timeline(self, value: int) -> None:
        if self.duration <= 0:
            return
        self.seek(value / 1000.0 * self.duration)

    def _show_frame(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb.shape
        qimage = QImage(rgb.data, width, height, channel * width, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        label_size = self.roi_selector.size()
        scaled = pixmap.scaled(
            label_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        left = (label_size.width() - scaled.width()) // 2
        top = (label_size.height() - scaled.height()) // 2
        self.roi_selector.setPixmap(scaled)
        self.roi_selector.set_display_pixmap_rect(QRect(left, top, scaled.width(), scaled.height()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_frame is not None:
            self._show_frame(self.current_frame)



from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QLabel


@dataclass(slots=True)
class RoiState:
    x: int = 0
    y: int = 0
    w: int = 1
    h: int = 1

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.w, self.h


class RoiSelector(QLabel):
    roi_changed = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(640, 360)
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Mở video để xem trước")
        self.setStyleSheet("background: #eaf3ff; color: #607089; border: 1px dashed #9ec5fe; border-radius: 10px;")
        self.video_width = 0
        self.video_height = 0
        self.roi = RoiState()
        self._dragging = False
        self._resizing = False
        self._drag_start = QPoint()
        self._start_roi = RoiState()
        self._pixmap_rect = QRect()

    def set_video_size(self, width: int, height: int) -> None:
        self.video_width = max(1, width)
        self.video_height = max(1, height)
        self.fit_bottom()

    def set_display_pixmap_rect(self, rect: QRect) -> None:
        self._pixmap_rect = rect

    def set_roi(self, roi: tuple[int, int, int, int]) -> None:
        x, y, w, h = roi
        self.roi = RoiState(x, y, w, h)
        self.update()
        self.roi_changed.emit(self.roi.as_tuple())

    def current_roi(self) -> tuple[int, int, int, int]:
        return self.roi.as_tuple()

    def fit_bottom(self) -> None:
        if not self.video_width or not self.video_height:
            return
        h = max(1, int(self.video_height * 0.25))
        self.set_roi((0, self.video_height - h, self.video_width, h))

    def reset_roi(self) -> None:
        if not self.video_width or not self.video_height:
            return
        self.set_roi((0, 0, self.video_width, self.video_height))

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.video_width or not self.video_height:
            return
        rect = self._roi_to_widget(self.roi)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#23c7d9"), 2))
        painter.drawRect(rect)
        painter.fillRect(rect, QColor(35, 199, 217, 34))
        painter.setPen(QPen(QColor("#35d8e8"), 1))
        painter.drawText(rect.adjusted(8, 8, -8, -8), Qt.AlignmentFlag.AlignTop, self._roi_text())
        painter.setBrush(QColor("#23c7d9"))
        for handle in self._handles(rect):
            painter.drawRect(handle)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.video_width:
            return
        rect = self._roi_to_widget(self.roi)
        self._drag_start = event.position().toPoint()
        self._start_roi = RoiState(*self.roi.as_tuple())
        self._resizing = self._on_handle(self._drag_start, rect)
        self._dragging = rect.contains(self._drag_start) and not self._resizing

    def mouseMoveEvent(self, event):
        point = event.position().toPoint()
        if not self.video_width:
            return
        if self._dragging:
            delta = self._widget_delta_to_video(point - self._drag_start)
            x = self._start_roi.x + delta.x()
            y = self._start_roi.y + delta.y()
            self._set_clamped(x, y, self._start_roi.w, self._start_roi.h)
        elif self._resizing:
            video_point = self._widget_to_video(point)
            x = self._start_roi.x
            y = self._start_roi.y
            w = max(1, video_point.x() - x)
            h = max(1, video_point.y() - y)
            self._set_clamped(x, y, w, h)
        else:
            rect = self._roi_to_widget(self.roi)
            self.setCursor(
                Qt.CursorShape.SizeFDiagCursor
                if self._on_handle(point, rect)
                else Qt.CursorShape.SizeAllCursor
                if rect.contains(point)
                else Qt.CursorShape.ArrowCursor
            )

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._resizing = False

    def _set_clamped(self, x: int, y: int, w: int, h: int) -> None:
        x = max(0, min(x, self.video_width - 1))
        y = max(0, min(y, self.video_height - 1))
        w = max(1, min(w, self.video_width - x))
        h = max(1, min(h, self.video_height - y))
        self.set_roi((x, y, w, h))

    def _roi_to_widget(self, roi: RoiState) -> QRect:
        scale_x = self._pixmap_rect.width() / self.video_width
        scale_y = self._pixmap_rect.height() / self.video_height
        return QRect(
            self._pixmap_rect.left() + int(roi.x * scale_x),
            self._pixmap_rect.top() + int(roi.y * scale_y),
            int(roi.w * scale_x),
            int(roi.h * scale_y),
        )

    def _widget_to_video(self, point: QPoint) -> QPoint:
        x = (point.x() - self._pixmap_rect.left()) / max(1, self._pixmap_rect.width())
        y = (point.y() - self._pixmap_rect.top()) / max(1, self._pixmap_rect.height())
        return QPoint(int(x * self.video_width), int(y * self.video_height))

    def _widget_delta_to_video(self, delta: QPoint) -> QPoint:
        return QPoint(
            int(delta.x() * self.video_width / max(1, self._pixmap_rect.width())),
            int(delta.y() * self.video_height / max(1, self._pixmap_rect.height())),
        )

    def _handles(self, rect: QRect) -> list[QRect]:
        size = 9
        return [
            QRect(rect.left() - 4, rect.top() - 4, size, size),
            QRect(rect.right() - 4, rect.top() - 4, size, size),
            QRect(rect.left() - 4, rect.bottom() - 4, size, size),
            QRect(rect.right() - 4, rect.bottom() - 4, size, size),
        ]

    def _on_handle(self, point: QPoint, rect: QRect) -> bool:
        return any(handle.contains(point) for handle in self._handles(rect))

    def _roi_text(self) -> str:
        return f"x={self.roi.x}, y={self.roi.y}, w={self.roi.w}, h={self.roi.h}"



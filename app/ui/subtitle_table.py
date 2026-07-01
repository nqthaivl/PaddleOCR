from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem

from app.models.subtitle import SubtitleSegment
from app.core.subtitle_exporter import format_srt_time


class SubtitleTable(QTableWidget):
    row_activated_time = pyqtSignal(float)

    HEADERS = ["#", "Bắt đầu", "Kết thúc", "Tin cậy", "Nội dung", "Thao tác"]

    def __init__(self):
        super().__init__(0, len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.cellDoubleClicked.connect(self._emit_time)
        self.horizontalHeader().setStretchLastSection(False)
        self.setColumnWidth(0, 54)
        self.setColumnWidth(1, 120)
        self.setColumnWidth(2, 120)
        self.setColumnWidth(3, 95)
        self.setColumnWidth(4, 520)
        self.setColumnWidth(5, 100)

    def set_segments(self, segments: list[SubtitleSegment]) -> None:
        self.setRowCount(0)
        for segment in segments:
            self.add_segment(segment)

    def add_segment(self, segment: SubtitleSegment) -> None:
        row = self.rowCount()
        self.insertRow(row)
        values = [
            str(segment.index),
            format_srt_time(segment.start),
            format_srt_time(segment.end),
            f"{segment.confidence:.2f}",
            segment.text,
            "Có thể sửa",
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col != 4:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if col == 3:
                self._paint_confidence(item, segment.confidence)
            item.setData(Qt.ItemDataRole.UserRole, segment.start)
            self.setItem(row, col, item)

    def segments(self) -> list[SubtitleSegment]:
        rows: list[SubtitleSegment] = []
        for row in range(self.rowCount()):
            start_text = self.item(row, 1).text()
            end_text = self.item(row, 2).text()
            confidence = float(self.item(row, 3).text())
            text = self.item(row, 4).text()
            rows.append(
                SubtitleSegment(
                    index=row + 1,
                    start=_parse_srt_time(start_text),
                    end=_parse_srt_time(end_text),
                    text=text,
                    confidence=confidence,
                )
            )
        return rows

    def filter_text(self, needle: str) -> None:
        needle = (needle or "").lower().strip()
        for row in range(self.rowCount()):
            text = self.item(row, 4).text().lower()
            self.setRowHidden(row, bool(needle and needle not in text))

    def _emit_time(self, row: int, col: int) -> None:
        item = self.item(row, 0)
        if item:
            self.row_activated_time.emit(float(item.data(Qt.ItemDataRole.UserRole) or 0.0))

    def _paint_confidence(self, item: QTableWidgetItem, confidence: float) -> None:
        if confidence < 0.65:
            item.setForeground(QColor("#f05f6b"))
        elif confidence < 0.82:
            item.setForeground(QColor("#f5b849"))
        else:
            item.setForeground(QColor("#35c983"))


def _parse_srt_time(value: str) -> float:
    time_part, millis_part = value.split(",")
    hours, minutes, seconds = [int(part) for part in time_part.split(":")]
    return hours * 3600 + minutes * 60 + seconds + int(millis_part) / 1000.0


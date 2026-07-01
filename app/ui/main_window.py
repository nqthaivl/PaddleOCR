from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSlider,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
    QStyle,
)

from app.core.preprocess import crop_roi, preprocess_for_ocr
from app.core.runtime import detect_runtime, preferred_to_use_gpu
from app.core.subtitle_exporter import export_subtitles
from app.core.video_reader import VideoReader
from app.models.settings import AppSettings, MergeSettings, PreprocessSettings, RuntimeSettings
from app.models.subtitle import SubtitleSegment
from app.ui.subtitle_table import SubtitleTable
from app.ui.video_preview import VideoPreview
from app.workers.ocr_worker import OcrWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HanSub OCR Studio")
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.resize(1360, 860)
        self.worker: OcrWorker | None = None
        self.video_path = ""
        self.last_segments: list[SubtitleSegment] = []

        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._build_top_bar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.video_preview = VideoPreview()
        self.video_preview.btn_preview_crop.clicked.connect(self.preview_crop)
        self.video_preview.timestamp_changed.connect(self._set_timestamp)
        splitter.addWidget(self.video_preview)
        splitter.addWidget(self._build_side_panel())
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm kiếm nội dung phụ đề...")
        self.search_input.textChanged.connect(self._filter_table)

        self.subtitle_table = SubtitleTable()
        self.subtitle_table.row_activated_time.connect(self.video_preview.seek)

        layout.addWidget(self.search_input)
        layout.addWidget(self.subtitle_table, 1)
        layout.addWidget(self._build_bottom_bar())

        self._apply_icons()
        self._refresh_runtime_status()
        self._log("Sẵn sàng. Hãy mở video để bắt đầu.")

    def _build_top_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("TopBar")
        layout = QHBoxLayout(frame)
        title = QLabel("HanSub OCR Studio")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Trích xuất phụ đề tiếng Trung bằng PaddleOCR")
        subtitle.setObjectName("MutedLabel")

        self.btn_open = QPushButton("Mở video")
        self.btn_save_project = QPushButton("Lưu dự án")
        self.btn_load_project = QPushButton("Mở dự án")
        self.btn_settings = QPushButton("Cài đặt")
        self.btn_help = QPushButton("Trợ giúp")

        self.btn_open.clicked.connect(self.open_video)
        self.btn_save_project.clicked.connect(self.save_project)
        self.btn_load_project.clicked.connect(self.load_project)
        self.btn_settings.clicked.connect(self.show_settings)
        self.btn_help.clicked.connect(self.show_help)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        for button in [
            self.btn_open,
            self.btn_save_project,
            self.btn_load_project,
            self.btn_settings,
            self.btn_help,
        ]:
            layout.addWidget(button)
        return frame

    def _build_side_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("SidePanel")
        layout = QVBoxLayout(frame)

        section = QLabel("Thiết lập OCR")
        section.setObjectName("SectionLabel")
        layout.addWidget(section)

        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText("Tệp video")
        self.btn_browse_video = QPushButton("Chọn")
        self.btn_browse_video.clicked.connect(self.open_video)

        video_row = QHBoxLayout()
        video_row.addWidget(self.video_input)
        video_row.addWidget(self.btn_browse_video)

        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Đường dẫn lưu phụ đề")
        self.btn_browse_output = QPushButton("Lưu tại")
        self.btn_browse_output.clicked.connect(self.choose_output)

        output_row = QHBoxLayout()
        output_row.addWidget(self.output_input)
        output_row.addWidget(self.btn_browse_output)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["SRT", "VTT", "ASS", "TXT"])
        self.format_combo.currentTextChanged.connect(self._update_output_extension)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["Tiếng Trung giản thể", "Tiếng Trung phồn thể", "Tiếng Trung + tiếng Anh"])

        self.frame_step = QDoubleSpinBox()
        self.frame_step.setRange(0.1, 5.0)
        self.frame_step.setSingleStep(0.1)
        self.frame_step.setValue(0.5)
        self.frame_step.setSuffix(" s")

        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(1, 100)
        self.confidence_slider.setValue(65)
        self.confidence_label = QLabel("65%")
        self.confidence_slider.valueChanged.connect(
            lambda value: self.confidence_label.setText(f"{value}%")
        )

        confidence_row = QHBoxLayout()
        confidence_row.addWidget(self.confidence_slider)
        confidence_row.addWidget(self.confidence_label)

        form = QFormLayout()
        form.addRow("Tệp video", video_row)
        form.addRow("Định dạng xuất", self.format_combo)
        form.addRow("Nơi lưu phụ đề", output_row)
        form.addRow("Ngôn ngữ", self.language_combo)
        form.addRow("Bước quét khung hình", self.frame_step)
        form.addRow("Độ tin cậy", confidence_row)
        layout.addLayout(form)

        self.chk_denoise = QCheckBox("Khử nhiễu")
        self.chk_upscale = QCheckBox("Phóng to 2x")
        self.chk_upscale.setChecked(True)
        self.chk_merge = QCheckBox("Tự gộp dòng trùng")
        self.chk_merge.setChecked(True)
        self.chk_grayscale = QCheckBox("Ảnh xám")
        self.chk_grayscale.setChecked(True)
        self.chk_contrast = QCheckBox("Tăng tương phản CLAHE")
        self.chk_contrast.setChecked(True)
        self.chk_threshold = QCheckBox("Ngưỡng thích nghi")

        self.runtime_combo = QComboBox()
        self.runtime_combo.addItem("Tự động tối ưu", "auto")
        self.runtime_combo.addItem("CPU", "cpu")
        self.runtime_combo.addItem("GPU", "gpu")
        self.runtime_combo.currentIndexChanged.connect(self._refresh_runtime_status)
        self.runtime_status_label = QLabel("")
        self.runtime_status_label.setObjectName("MutedLabel")

        for checkbox in [
            self.chk_denoise,
            self.chk_upscale,
            self.chk_merge,
            self.chk_grayscale,
            self.chk_contrast,
            self.chk_threshold,
        ]:
            layout.addWidget(checkbox)

        self.btn_auto_roi = QPushButton("Tự chọn vùng phụ đề")
        self.btn_auto_roi.clicked.connect(self.auto_detect_roi)
        runtime_form = QFormLayout()
        runtime_form.addRow("Thiết bị xử lý", self.runtime_combo)
        layout.addLayout(runtime_form)
        layout.addWidget(self.runtime_status_label)

        layout.addWidget(self.btn_auto_roi)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(180)
        layout.addWidget(QLabel("Nhật ký"))
        layout.addWidget(self.log_box, 1)

        return frame

    def _build_bottom_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("BottomBar")
        layout = QHBoxLayout(frame)

        self.status_label = QLabel("Sẵn sàng")
        self.status_label.setObjectName("MutedLabel")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)

        self.btn_start = QPushButton("Bắt đầu OCR")
        self.btn_start.setObjectName("PrimaryButton")
        self.btn_stop = QPushButton("Dừng")
        self.btn_stop.setObjectName("DangerButton")
        self.btn_resume = QPushButton("Chạy tiếp")
        self.btn_export = QPushButton("Xuất phụ đề")

        self.btn_start.clicked.connect(self.start_ocr)
        self.btn_stop.clicked.connect(self.stop_ocr)
        self.btn_resume.clicked.connect(self.start_ocr)
        self.btn_export.clicked.connect(self.export_current)

        layout.addWidget(self.status_label, 2)
        layout.addWidget(self.progress, 5)
        for button in [self.btn_start, self.btn_stop, self.btn_resume, self.btn_export]:
            layout.addWidget(button)
        return frame

    def _apply_icons(self) -> None:
        icon_size = QSize(18, 18)
        icon_map = {
            self.btn_open: QStyle.StandardPixmap.SP_DirOpenIcon,
            self.btn_save_project: QStyle.StandardPixmap.SP_DialogSaveButton,
            self.btn_load_project: QStyle.StandardPixmap.SP_DirIcon,
            self.btn_settings: QStyle.StandardPixmap.SP_FileDialogDetailedView,
            self.btn_help: QStyle.StandardPixmap.SP_MessageBoxQuestion,
            self.btn_browse_video: QStyle.StandardPixmap.SP_DirOpenIcon,
            self.btn_browse_output: QStyle.StandardPixmap.SP_DialogSaveButton,
            self.btn_auto_roi: QStyle.StandardPixmap.SP_DialogApplyButton,
            self.btn_start: QStyle.StandardPixmap.SP_MediaPlay,
            self.btn_stop: QStyle.StandardPixmap.SP_MediaStop,
            self.btn_resume: QStyle.StandardPixmap.SP_BrowserReload,
            self.btn_export: QStyle.StandardPixmap.SP_DialogSaveButton,
        }
        for button, standard_icon in icon_map.items():
            button.setIcon(self.style().standardIcon(standard_icon))
            button.setIconSize(icon_size)
    def open_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Mở video",
            "",
            "Tệp video (*.mp4 *.mkv *.avi *.mov *.flv *.wmv);;Tất cả tệp (*.*)",
        )
        if not path:
            return
        try:
            self.video_path = path
            self.video_input.setText(path)
            self.video_preview.load_video(path)
            self.output_input.setText(VideoReader.default_output_path(path, self.format_combo.currentText()))
            self._log(f"Đã mở video: {path}")
        except Exception as exc:
            self._error(str(exc))

    def choose_output(self) -> None:
        fmt = self.format_combo.currentText().lower()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu phụ đề",
            self.output_input.text() or f"subtitle.{fmt}",
            f"{fmt.upper()} (*.{fmt});;Tất cả tệp (*.*)",
        )
        if path:
            self.output_input.setText(path)

    def start_ocr(self) -> None:
        if self.worker and self.worker.isRunning():
            self._log("OCR đang chạy.")
            return
        if not self.video_path:
            self._error("Vui lòng mở video trước.")
            return

        settings = self._settings()
        self.progress.setValue(0)
        self.subtitle_table.setRowCount(0)
        self.last_segments = []
        self.worker = OcrWorker(self.video_path, self.video_preview.current_roi(), settings)
        self.worker.progress_changed.connect(self.progress.setValue)
        self.worker.sample_ready.connect(self._on_sample)
        self.worker.segments_ready.connect(self._on_segments)
        self.worker.status_changed.connect(self._set_status)
        self.worker.failed.connect(self._error)
        self.worker.finished_ok.connect(lambda: self._log("OCR đã xong. Hãy xem lại và xuất phụ đề."))
        self.worker.start()

    def stop_ocr(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self._log("Đã yêu cầu dừng OCR.")

    def export_current(self) -> None:
        path = self.output_input.text().strip()
        if not path:
            self.choose_output()
            path = self.output_input.text().strip()
        if not path:
            return
        segments = self.subtitle_table.segments()
        if not segments:
            self._error("Chưa có đoạn phụ đề để xuất.")
            return
        try:
            export_subtitles(path, self.format_combo.currentText(), segments)
            self._log(f"Đã xuất {len(segments)} đoạn phụ đề vào {path}")
            QMessageBox.information(self, "Xuất phụ đề hoàn tất", f"Đã lưu phụ đề:\n{path}")
        except Exception as exc:
            self._error(str(exc))

    def preview_crop(self) -> None:
        frame = self.video_preview.current_frame
        if frame is None:
            self._error("Vui lòng mở video trước.")
            return
        try:
            settings = self._settings()
            raw_crop = crop_roi(frame, self.video_preview.current_roi())
            processed = preprocess_for_ocr(frame, self.video_preview.current_roi(), settings.preprocess)
            self._show_crop_dialog(raw_crop, processed)
        except Exception as exc:
            self._error(str(exc))

    def auto_detect_roi(self) -> None:
        self.video_preview.roi_selector.fit_bottom()
        self._log("Đã tự chọn 25% phía dưới video làm vùng phụ đề. Bạn có thể chỉnh tay nếu cần.")

    def save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Lưu dự án", "hansub_project.json", "JSON (*.json)")
        if not path:
            return
        data = {
            "video_path": self.video_path,
            "output_path": self.output_input.text(),
            "format": self.format_combo.currentText(),
            "language": self.language_combo.currentText(),
            "frame_step": self.frame_step.value(),
            "confidence": self.confidence_slider.value(),
            "roi": self.video_preview.current_roi(),
            "preprocess": {
                "denoise": self.chk_denoise.isChecked(),
                "upscale": self.chk_upscale.isChecked(),
                "grayscale": self.chk_grayscale.isChecked(),
                "contrast": self.chk_contrast.isChecked(),
                "threshold": self.chk_threshold.isChecked(),
            },
            "runtime": {"device_mode": self.runtime_combo.currentData(), "use_gpu": preferred_to_use_gpu(self.runtime_combo.currentData())},
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._log(f"Đã lưu dự án: {path}")

    def load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Mở dự án", "", "JSON (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            video_path = data.get("video_path") or ""
            if video_path and Path(video_path).exists():
                self.video_path = video_path
                self.video_input.setText(video_path)
                self.video_preview.load_video(video_path)
            self.output_input.setText(data.get("output_path", ""))
            self.format_combo.setCurrentText(data.get("format", "SRT"))
            self.language_combo.setCurrentText(data.get("language", "Tiếng Trung giản thể"))
            self.frame_step.setValue(float(data.get("frame_step", 0.5)))
            self.confidence_slider.setValue(int(data.get("confidence", 65)))
            roi = data.get("roi")
            if roi:
                self.video_preview.roi_selector.set_roi(tuple(roi))
            preprocess = data.get("preprocess", {})
            self.chk_denoise.setChecked(bool(preprocess.get("denoise", False)))
            self.chk_upscale.setChecked(bool(preprocess.get("upscale", True)))
            self.chk_grayscale.setChecked(bool(preprocess.get("grayscale", True)))
            self.chk_contrast.setChecked(bool(preprocess.get("contrast", True)))
            self.chk_threshold.setChecked(bool(preprocess.get("threshold", False)))
            runtime = data.get("runtime", {})
            mode = runtime.get("device_mode")
            if mode is None:
                old_use_gpu = runtime.get("use_gpu", None)
                mode = "auto" if old_use_gpu is None else "gpu" if old_use_gpu else "cpu"
            index = self.runtime_combo.findData(mode)
            if index >= 0:
                self.runtime_combo.setCurrentIndex(index)
            self._refresh_runtime_status()
            self._log(f"Đã mở dự án: {path}")
        except Exception as exc:
            self._error(str(exc))

    def _refresh_runtime_status(self) -> None:
        if not hasattr(self, "runtime_combo"):
            return
        mode = self.runtime_combo.currentData() or "auto"
        probe = detect_runtime(mode)
        self.runtime_status_label.setText(probe.message)
    def show_settings(self) -> None:
        QMessageBox.information(
            self,
            "Cài đặt",
            "Pipeline mặc định: cắt vùng ROI, phóng to 2x, ảnh xám, tăng tương phản CLAHE, làm nét, "
            "OCR tiếng Trung bằng PaddleOCR, gộp dòng trùng bằng fuzzy matching, rồi xuất SRT/VTT/ASS/TXT.",
        )

    def show_help(self) -> None:
        QMessageBox.information(
            self,
            "Trợ giúp",
            "1. Mở video\n"
            "2. Kéo hoặc chỉnh vùng chọn màu xanh lên khu vực phụ đề\n"
            "3. Chọn ngôn ngữ OCR, bước quét, độ tin cậy và định dạng xuất\n"
            "4. Bắt đầu OCR\n"
            "5. Xem lại hoặc sửa nội dung trong bảng\n"
            "6. Xuất phụ đề",
        )

    def _settings(self) -> AppSettings:
        preprocess = PreprocessSettings(
            upscale=self.chk_upscale.isChecked(),
            denoise=self.chk_denoise.isChecked(),
            grayscale=self.chk_grayscale.isChecked(),
            contrast=self.chk_contrast.isChecked(),
            threshold=self.chk_threshold.isChecked(),
        )
        merge = MergeSettings(
            duplicate_similarity=0.85 if self.chk_merge.isChecked() else 1.01,
            max_blank_gap_seconds=1.0,
        )
        device_mode = self.runtime_combo.currentData() or "auto"
        runtime = RuntimeSettings(use_gpu=preferred_to_use_gpu(device_mode), device_mode=device_mode, batch_size=1)
        return AppSettings(
            language=self.language_combo.currentText(),
            output_format=self.format_combo.currentText(),
            frame_step_seconds=self.frame_step.value(),
            confidence_threshold=self.confidence_slider.value() / 100.0,
            roi_mode="manual",
            preprocess=preprocess,
            merge=merge,
            runtime=runtime,
        )

    def _on_sample(self, timestamp: float, text: str, confidence: float) -> None:
        self._log(f"{timestamp:.2f}s | {confidence:.2f} | {text}")

    def _on_segments(self, segments: list) -> None:
        self.last_segments = list(segments)
        self.subtitle_table.set_segments(self.last_segments)
        self._log(f"Đã tạo {len(self.last_segments)} đoạn phụ đề.")

    def _set_status(self, message: str) -> None:
        self.status_label.setText(message)

    def _set_timestamp(self, timestamp: float) -> None:
        self.status_label.setText(f"Xem trước {timestamp:.2f}s")

    def _filter_table(self, text: str) -> None:
        self.subtitle_table.filter_text(text)

    def _update_output_extension(self, fmt: str) -> None:
        current = self.output_input.text().strip()
        if current:
            self.output_input.setText(str(Path(current).with_suffix(f".{fmt.lower()}")))

    def _show_crop_dialog(self, raw_crop, processed) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Xem vùng cắt")
        layout = QHBoxLayout(dialog)
        for title, image in [("Vùng cắt gốc", raw_crop), ("Vùng sau xử lý", processed)]:
            box = QVBoxLayout()
            box.addWidget(QLabel(title))
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setPixmap(_pixmap_from_bgr(image).scaled(
                520,
                260,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            box.addWidget(label)
            layout.addLayout(box)
        dialog.resize(1100, 360)
        dialog.exec()

    def _log(self, message: str) -> None:
        self.log_box.append(message)
        self.status_label.setText(message)

    def _error(self, message: str) -> None:
        self._log(f"Lỗi: {message}")
        QMessageBox.critical(self, "Lỗi", message)


def _pixmap_from_bgr(image) -> QPixmap:
    import cv2
    from PyQt6.QtGui import QImage

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    height, width, channel = rgb.shape
    qimage = QImage(rgb.data, width, height, channel * width, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage)


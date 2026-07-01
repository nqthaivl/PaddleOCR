from __future__ import annotations

import os
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def load_stylesheet(app: QApplication) -> None:
    qss_path = Path(__file__).parent / "ui" / "styles.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def main() -> int:
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("HanSub OCR Studio")
    qt_app.setOrganizationName("HanSub")
    load_stylesheet(qt_app)

    window = MainWindow()
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

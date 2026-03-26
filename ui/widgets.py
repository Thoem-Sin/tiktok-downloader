from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QProgressBar, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette

from core.queue_manager import DownloadItem, DownloadStatus


STATUS_COLORS = {
    DownloadStatus.PENDING:     "#8892a4",
    DownloadStatus.DOWNLOADING: "#4fc3f7",
    DownloadStatus.DONE:        "#69f0ae",
    DownloadStatus.FAILED:      "#ef5350",
    DownloadStatus.CANCELLED:   "#ffa726",
}


class DownloadItemWidget(QWidget):
    """Row widget showing a single download item's state."""

    remove_requested = Signal(str)  # url

    def __init__(self, item: DownloadItem, parent=None):
        super().__init__(parent)
        self.item = item
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Status dot
        self.dot = QLabel("●")
        self.dot.setFixedWidth(16)
        self.dot.setAlignment(Qt.AlignCenter)

        # URL label
        self.url_label = QLabel(self.item.display_url())
        self.url_label.setFixedWidth(340)
        self.url_label.setStyleSheet("color: #cdd6f4; font-size: 12px;")

        # Status label
        self.status_label = QLabel(self.item.status.value)
        self.status_label.setFixedWidth(90)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 11px; font-weight: 600;")

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(self.item.progress)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(140)

        # Speed label
        self.speed_label = QLabel("")
        self.speed_label.setFixedWidth(80)
        self.speed_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.speed_label.setStyleSheet("color: #a6adc8; font-size: 11px;")

        # Remove button
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedSize(22, 22)
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6c7086;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover { color: #ef5350; }
        """)
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.item.url))

        layout.addWidget(self.dot)
        layout.addWidget(self.url_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.speed_label)
        layout.addStretch()
        layout.addWidget(self.remove_btn)

        self.setStyleSheet("""
            DownloadItemWidget {
                background: #1e2030;
                border-radius: 6px;
            }
            DownloadItemWidget:hover {
                background: #252740;
            }
        """)
        self.setFixedHeight(44)
        self.refresh()

    def refresh(self):
        color = STATUS_COLORS.get(self.item.status, "#8892a4")
        self.dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        self.status_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {color};"
        )
        self.status_label.setText(self.item.status.value)
        self.progress_bar.setValue(self.item.progress)
        self.speed_label.setText(self.item.speed)

        # Style progress bar based on status
        if self.item.status == DownloadStatus.DONE:
            chunk_color = "#69f0ae"
        elif self.item.status == DownloadStatus.FAILED:
            chunk_color = "#ef5350"
        else:
            chunk_color = "#4fc3f7"

        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: #313244;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {chunk_color};
                border-radius: 3px;
            }}
        """)

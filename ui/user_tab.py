import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QScrollArea, QSpinBox, QProgressBar, QFrame
)
from PySide6.QtCore import Qt

from core.worker import UserDownloadWorker
from core.queue_manager import DownloadItem, DownloadStatus
from ui.widgets import DownloadItemWidget


class UserTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_dir = os.path.expanduser("~/Downloads")
        self._worker: UserDownloadWorker | None = None
        self._item_widgets: dict[str, DownloadItemWidget] = {}
        self._items: dict[str, DownloadItem] = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 12)

        # ── Username row
        user_hint = QLabel("TIKTOK USERNAME")
        user_hint.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;")

        user_row = QHBoxLayout()
        user_row.setSpacing(8)

        at_label = QLabel("@")
        at_label.setStyleSheet("font-size: 16px; color: #89b4fa; font-weight: 700;")
        at_label.setFixedWidth(16)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("username")
        self.username_input.returnPressed.connect(self._start_download)

        max_label = QLabel("Max videos:")
        max_label.setStyleSheet("color: #6c7086; font-size: 12px;")
        max_label.setFixedWidth(80)

        self.max_spin = QSpinBox()
        self.max_spin.setRange(0, 10000)
        self.max_spin.setValue(0)
        self.max_spin.setFixedWidth(72)
        self.max_spin.setToolTip("0 = download all")

        zero_hint = QLabel("(0 = all)")
        zero_hint.setStyleSheet("color: #45475a; font-size: 11px;")

        user_row.addWidget(at_label)
        user_row.addWidget(self.username_input, 1)
        user_row.addSpacing(16)
        user_row.addWidget(max_label)
        user_row.addWidget(self.max_spin)
        user_row.addWidget(zero_hint)

        # ── Folder row
        folder_hint = QLabel("SAVE FOLDER")
        folder_hint.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;")

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)

        folder_icon = QLabel("📁")
        folder_icon.setFixedWidth(20)

        self.folder_label = QLineEdit(self._save_dir)
        self.folder_label.setReadOnly(True)
        self.folder_label.setStyleSheet("color: #a6adc8;")

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(90)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_folder)

        folder_row.addWidget(folder_icon)
        folder_row.addWidget(self.folder_label, 1)
        folder_row.addWidget(browse_btn)

        # ── Control buttons
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self.start_btn = QPushButton("⬇  Fetch & Download All")
        self.start_btn.setObjectName("primary")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self._start_download)

        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setFixedWidth(80)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_download)

        ctrl_row.addWidget(self.start_btn)
        ctrl_row.addWidget(self.stop_btn)
        ctrl_row.addStretch()

        # ── Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #313244;")

        # ── Progress row (status + bar + summary inline)
        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self.status_label.setMinimumWidth(200)

        self.overall_bar = QProgressBar()
        self.overall_bar.setRange(0, 100)
        self.overall_bar.setValue(0)
        self.overall_bar.setTextVisible(False)
        self.overall_bar.setFixedHeight(6)
        self.overall_bar.setStyleSheet("""
            QProgressBar { background: #313244; border-radius: 3px; }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #89b4fa, stop:1 #cba6f7);
                border-radius: 3px;
            }
        """)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #585b70; font-size: 11px;")
        self.summary_label.setFixedWidth(220)
        self.summary_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        progress_row.addWidget(self.status_label, 1)
        progress_row.addWidget(self.overall_bar, 2)
        progress_row.addWidget(self.summary_label)

        # ── Videos label
        list_hint = QLabel("VIDEOS")
        list_hint.setObjectName("section")

        # ── Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(3)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.addStretch()
        scroll.setWidget(self.list_container)

        root.addWidget(user_hint)
        root.addLayout(user_row)
        root.addSpacing(4)
        root.addWidget(folder_hint)
        root.addLayout(folder_row)
        root.addLayout(ctrl_row)
        root.addWidget(divider)
        root.addLayout(progress_row)
        root.addWidget(list_hint)
        root.addWidget(scroll, 1)

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Folder", self._save_dir)
        if path:
            self._save_dir = path
            self.folder_label.setText(path)

    def _start_download(self):
        username = self.username_input.text().strip().lstrip("@")
        if not username:
            self.status_label.setText("⚠  Please enter a username.")
            return

        for w in list(self._item_widgets.values()):
            self.list_layout.removeWidget(w)
            w.deleteLater()
        self._item_widgets.clear()
        self._items.clear()
        self.overall_bar.setValue(0)
        self.summary_label.setText("")

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText(f"Connecting to @{username}…")

        self._worker = UserDownloadWorker(
            username=username,
            save_dir=self._save_dir,
            max_videos=self.max_spin.value(),
        )
        self._worker.video_found.connect(self._on_video_found)
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._on_status)
        self._worker.video_done.connect(self._on_video_done)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _stop_download(self):
        if self._worker:
            self._worker.cancel()
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(True)
        self.status_label.setText("Stopped by user.")

    def _on_video_found(self, url: str):
        if url in self._items:
            return
        item = DownloadItem(url=url, status=DownloadStatus.PENDING)
        self._items[url] = item
        widget = DownloadItemWidget(item)
        self._item_widgets[url] = widget
        self.list_layout.insertWidget(self.list_layout.count() - 1, widget)

    def _on_progress(self, current: int, total: int):
        if total > 0:
            self.overall_bar.setValue(int(current / total * 100))

    def _on_status(self, msg: str):
        self.status_label.setText(msg)

    def _on_video_done(self, url: str, success: bool, msg: str):
        item = self._items.get(url)
        if item:
            item.status = DownloadStatus.DONE if success else DownloadStatus.FAILED
            item.progress = 100 if success else 50
            self._item_widgets[url].refresh()

        done = sum(1 for i in self._items.values() if i.status == DownloadStatus.DONE)
        failed = sum(1 for i in self._items.values() if i.status == DownloadStatus.FAILED)
        self.summary_label.setText(f"Done: {done}   Failed: {failed}   Total: {len(self._items)}")

    def _on_finished(self, success: int, fail: int):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.overall_bar.setValue(100)
        self.status_label.setText(f"✓  Finished — {success} downloaded, {fail} failed.")
        self.summary_label.setText(
            f"Done: {success}   Failed: {fail}   Total: {len(self._items)}"
        )

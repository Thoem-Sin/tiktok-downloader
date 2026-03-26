import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QFileDialog, QLineEdit,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt

from core.worker import DownloadWorker
from core.queue_manager import DownloadItem, DownloadStatus
from ui.widgets import DownloadItemWidget


class BatchTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: dict[str, DownloadItem] = {}
        self._item_widgets: dict[str, DownloadItemWidget] = {}
        self._workers: dict[str, DownloadWorker] = {}
        self._save_dir: str = os.path.expanduser("~/Downloads")
        self._max_concurrent = 3
        self._active_count = 0
        self._pending_queue: list[str] = []
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 12)

        # ── URL input
        url_hint = QLabel("Paste TikTok URLs — one per line")
        url_hint.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;")

        self.url_input = QPlainTextEdit()
        self.url_input.setPlaceholderText(
            "https://www.tiktok.com/@user/video/123456789\nhttps://vm.tiktok.com/shortlink\n..."
        )
        self.url_input.setFixedHeight(96)

        # ── Folder + action row
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

        self.add_btn = QPushButton("＋  Add to Queue")
        self.add_btn.setObjectName("primary")
        self.add_btn.setFixedWidth(140)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_urls)

        self.clear_input_btn = QPushButton("Clear")
        self.clear_input_btn.setFixedWidth(68)
        self.clear_input_btn.setCursor(Qt.PointingHandCursor)
        self.clear_input_btn.clicked.connect(self.url_input.clear)

        folder_row.addWidget(folder_icon)
        folder_row.addWidget(self.folder_label, 1)
        folder_row.addWidget(browse_btn)
        folder_row.addSpacing(12)
        folder_row.addWidget(self.add_btn)
        folder_row.addWidget(self.clear_input_btn)

        # ── Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #313244;")

        # ── Queue header
        queue_header = QHBoxLayout()
        queue_header.setSpacing(8)

        self.queue_count_label = QLabel("QUEUE  ·  0 ITEMS")
        self.queue_count_label.setObjectName("section")

        start_btn = QPushButton("▶  Start All")
        start_btn.setObjectName("primary")
        start_btn.setFixedWidth(110)
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.clicked.connect(self._start_all)

        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setFixedWidth(80)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self._stop_all)

        clear_done_btn = QPushButton("Clear Done")
        clear_done_btn.setFixedWidth(90)
        clear_done_btn.setCursor(Qt.PointingHandCursor)
        clear_done_btn.clicked.connect(self._clear_done)

        queue_header.addWidget(self.queue_count_label)
        queue_header.addStretch()
        queue_header.addWidget(clear_done_btn)
        queue_header.addWidget(self.stop_btn)
        queue_header.addWidget(start_btn)

        # ── Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.queue_container = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setSpacing(3)
        self.queue_layout.setContentsMargins(0, 0, 4, 0)
        self.queue_layout.addStretch()
        scroll.setWidget(self.queue_container)

        # ── Summary
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #585b70; font-size: 11px;")

        root.addWidget(url_hint)
        root.addWidget(self.url_input)
        root.addLayout(folder_row)
        root.addWidget(divider)
        root.addLayout(queue_header)
        root.addWidget(scroll, 1)
        root.addWidget(self.summary_label)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Folder", self._save_dir)
        if path:
            self._save_dir = path
            self.folder_label.setText(path)

    def _add_urls(self):
        text = self.url_input.toPlainText().strip()
        if not text:
            return

        for line in text.splitlines():
            url = line.strip()
            if url and url not in self._items:
                item = DownloadItem(url=url)
                self._items[url] = item
                widget = DownloadItemWidget(item)
                widget.remove_requested.connect(self._remove_item)
                self._item_widgets[url] = widget
                self.queue_layout.insertWidget(self.queue_layout.count() - 1, widget)

        self.url_input.clear()
        self._update_counts()

    def _remove_item(self, url: str):
        if url in self._workers:
            self._workers[url].cancel()
            self._workers.pop(url, None)

        widget = self._item_widgets.pop(url, None)
        if widget:
            self.queue_layout.removeWidget(widget)
            widget.deleteLater()

        self._items.pop(url, None)
        if url in self._pending_queue:
            self._pending_queue.remove(url)
        self._update_counts()

    def _start_all(self):
        self._pending_queue = [
            url for url, item in self._items.items()
            if item.status == DownloadStatus.PENDING
        ]
        self._dispatch_next()

    def _dispatch_next(self):
        while self._active_count < self._max_concurrent and self._pending_queue:
            url = self._pending_queue.pop(0)
            item = self._items.get(url)
            if not item or item.status != DownloadStatus.PENDING:
                continue
            self._start_single(url)

    def _start_single(self, url: str):
        item = self._items[url]
        item.status = DownloadStatus.DOWNLOADING
        item.progress = 0
        self._item_widgets[url].refresh()
        self._active_count += 1

        worker = DownloadWorker(url=url, save_dir=self._save_dir)  # title filename, no watermark
        worker.progress.connect(lambda v, u=url: self._on_progress(u, v))
        worker.speed.connect(lambda s, u=url: self._on_speed(u, s))
        worker.finished.connect(lambda ok, msg, u=url: self._on_finished(u, ok, msg))
        self._workers[url] = worker
        worker.start()

    def _on_progress(self, url: str, value: int):
        item = self._items.get(url)
        if item:
            item.progress = value
            self._item_widgets[url].refresh()

    def _on_speed(self, url: str, speed: str):
        item = self._items.get(url)
        if item:
            item.speed = speed
            self._item_widgets[url].refresh()

    def _on_finished(self, url: str, success: bool, msg: str):
        item = self._items.get(url)
        if item:
            item.status = DownloadStatus.DONE if success else DownloadStatus.FAILED
            item.progress = 100 if success else item.progress
            item.message = msg
            item.speed = ""
            self._item_widgets[url].refresh()

        self._workers.pop(url, None)
        self._active_count = max(0, self._active_count - 1)
        self._update_counts()
        self._dispatch_next()

    def _stop_all(self):
        for worker in list(self._workers.values()):
            worker.cancel()
        self._pending_queue.clear()

        for url, item in self._items.items():
            if item.status in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING):
                item.status = DownloadStatus.CANCELLED
                item.speed = ""
                self._item_widgets[url].refresh()

        self._active_count = 0
        self._update_counts()

    def _clear_done(self):
        done_urls = [
            url for url, item in self._items.items()
            if item.status in (DownloadStatus.DONE, DownloadStatus.CANCELLED, DownloadStatus.FAILED)
        ]
        for url in done_urls:
            self._remove_item(url)

    def _update_counts(self):
        total = len(self._items)
        done = sum(1 for i in self._items.values() if i.status == DownloadStatus.DONE)
        failed = sum(1 for i in self._items.values() if i.status == DownloadStatus.FAILED)
        active = sum(1 for i in self._items.values() if i.status == DownloadStatus.DOWNLOADING)

        self.queue_count_label.setText(f"QUEUE  ·  {total} ITEMS")
        self.summary_label.setText(
            f"Done: {done}   Active: {active}   Failed: {failed}   Total: {total}"
            if total else ""
        )


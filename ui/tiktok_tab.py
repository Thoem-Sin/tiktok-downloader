import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QFileDialog, QLineEdit, QScrollArea,
    QFrame, QTabWidget, QSpinBox, QProgressBar
)
from PySide6.QtCore import Qt

from core.worker import DownloadWorker, UserDownloadWorker
from core.queue_manager import DownloadItem, DownloadStatus
from ui.widgets import DownloadItemWidget

_SUB_TAB_STYLE = """
    QTabWidget::pane { border: none; background: transparent; padding: 0; }
    QTabBar::tab {
        background: transparent;
        color: #6c7086;
        padding: 6px 16px;
        border: none;
        border-bottom: 2px solid transparent;
        margin-right: 4px;
        font-size: 12px;
        font-weight: 600;
    }
    QTabBar::tab:selected { color: #89b4fa; border-bottom: 2px solid #89b4fa; }
    QTabBar::tab:hover:!selected { color: #a6adc8; }
"""


class TikTokTab(QWidget):
    """Top-level TikTok tab with shared folder picker and sub-tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_dir = os.path.expanduser("~/Downloads")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 12)

        # ── Shared save-folder row
        folder_hint = QLabel("SAVE FOLDER")
        folder_hint.setStyleSheet(
            "color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;"
        )

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

        # ── Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #313244;")

        # ── Sub-tabs
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet(_SUB_TAB_STYLE)

        self.batch_widget = _BatchWidget(self)
        self.user_widget  = _UserWidget(self)

        self.sub_tabs.addTab(self.batch_widget, "Batch URLs")
        self.sub_tabs.addTab(self.user_widget,  "By Username")

        root.addWidget(folder_hint)
        root.addLayout(folder_row)
        root.addWidget(divider)
        root.addWidget(self.sub_tabs, 1)

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Folder", self._save_dir)
        if path:
            self._save_dir = path
            self.folder_label.setText(path)

    def save_dir(self) -> str:
        return self._save_dir


# ── Batch URLs sub-widget ──────────────────────────────────────────────────────

class _BatchWidget(QWidget):
    def __init__(self, tiktok_tab: TikTokTab):
        super().__init__()
        self._tt = tiktok_tab
        self._items: dict[str, DownloadItem] = {}
        self._item_widgets: dict[str, DownloadItemWidget] = {}
        self._workers: dict[str, DownloadWorker] = {}
        self._max_concurrent = 3
        self._active = 0
        self._pending: list[str] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(0, 10, 0, 0)

        # URL input
        hint = QLabel("PASTE TIKTOK URLS — ONE PER LINE")
        hint.setStyleSheet(
            "color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;"
        )

        self.url_input = QPlainTextEdit()
        self.url_input.setPlaceholderText(
            "https://www.tiktok.com/@user/video/123456789\nhttps://vm.tiktok.com/shortlink\n..."
        )
        self.url_input.setFixedHeight(90)

        # Action row
        action_row = QHBoxLayout()
        self.add_btn = QPushButton("＋  Add to Queue")
        self.add_btn.setObjectName("primary")
        self.add_btn.setFixedWidth(130)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_urls)

        clear_input_btn = QPushButton("Clear")
        clear_input_btn.setFixedWidth(70)
        clear_input_btn.setCursor(Qt.PointingHandCursor)
        clear_input_btn.clicked.connect(self.url_input.clear)

        action_row.addWidget(self.add_btn)
        action_row.addWidget(clear_input_btn)
        action_row.addStretch()

        # Queue header
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #313244;")

        queue_header = QHBoxLayout()
        self.count_label = QLabel("QUEUE  ·  0 ITEMS")
        self.count_label.setObjectName("section")

        start_btn = QPushButton("▶ Start All")
        start_btn.setObjectName("primary")
        start_btn.setFixedWidth(106)
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.clicked.connect(self._start_all)

        stop_btn = QPushButton("■ Stop")
        stop_btn.setObjectName("danger")
        stop_btn.setFixedWidth(76)
        stop_btn.setCursor(Qt.PointingHandCursor)
        stop_btn.clicked.connect(self._stop_all)

        clear_done_btn = QPushButton("Clear Done")
        clear_done_btn.setFixedWidth(100)
        clear_done_btn.setCursor(Qt.PointingHandCursor)
        clear_done_btn.clicked.connect(self._clear_done)

        queue_header.addWidget(self.count_label)
        queue_header.addStretch()
        queue_header.addWidget(clear_done_btn)
        queue_header.addWidget(stop_btn)
        queue_header.addWidget(start_btn)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.queue_container = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setSpacing(3)
        self.queue_layout.setContentsMargins(0, 0, 4, 0)
        self.queue_layout.addStretch()
        scroll.setWidget(self.queue_container)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #585b70; font-size: 11px;")

        root.addWidget(hint)
        root.addWidget(self.url_input)
        root.addLayout(action_row)
        root.addWidget(divider)
        root.addLayout(queue_header)
        root.addWidget(scroll, 1)
        root.addWidget(self.summary_label)

    def _add_urls(self):
        text = self.url_input.toPlainText().strip()
        if not text:
            return
        for line in text.splitlines():
            url = line.strip()
            if url and url not in self._items:
                item = DownloadItem(url=url)
                self._items[url] = item
                w = DownloadItemWidget(item)
                w.remove_requested.connect(self._remove_item)
                self._item_widgets[url] = w
                self.queue_layout.insertWidget(self.queue_layout.count() - 1, w)
        self.url_input.clear()
        self._update_counts()

    def _remove_item(self, url: str):
        if url in self._workers:
            self._workers[url].cancel()
            self._workers.pop(url, None)
        w = self._item_widgets.pop(url, None)
        if w:
            self.queue_layout.removeWidget(w)
            w.deleteLater()
        self._items.pop(url, None)
        if url in self._pending:
            self._pending.remove(url)
        self._update_counts()

    def _start_all(self):
        self._pending = [u for u, i in self._items.items()
                         if i.status == DownloadStatus.PENDING]
        self._dispatch()

    def _dispatch(self):
        while self._active < self._max_concurrent and self._pending:
            url = self._pending.pop(0)
            item = self._items.get(url)
            if not item or item.status != DownloadStatus.PENDING:
                continue
            self._start_single(url)

    def _start_single(self, url: str):
        item = self._items[url]
        item.status = DownloadStatus.DOWNLOADING
        item.progress = 0
        self._item_widgets[url].refresh()
        self._active += 1

        worker = DownloadWorker(url=url, save_dir=self._tt.save_dir())
        worker.progress.connect(lambda v, u=url: self._on_progress(u, v))
        worker.speed.connect(lambda s, u=url: self._on_speed(u, s))
        worker.finished.connect(lambda ok, msg, u=url: self._on_finished(u, ok, msg))
        self._workers[url] = worker
        worker.start()

    def _on_progress(self, url, v):
        item = self._items.get(url)
        if item:
            item.progress = v
            self._item_widgets[url].refresh()

    def _on_speed(self, url, s):
        item = self._items.get(url)
        if item:
            item.speed = s
            self._item_widgets[url].refresh()

    def _on_finished(self, url, ok, msg):
        item = self._items.get(url)
        if item:
            item.status = DownloadStatus.DONE if ok else DownloadStatus.FAILED
            item.progress = 100 if ok else item.progress
            item.speed = ""
            self._item_widgets[url].refresh()
        self._workers.pop(url, None)
        self._active = max(0, self._active - 1)
        self._update_counts()
        self._dispatch()

    def _stop_all(self):
        for w in list(self._workers.values()):
            w.cancel()
        self._pending.clear()
        for url, item in self._items.items():
            if item.status in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING):
                item.status = DownloadStatus.CANCELLED
                item.speed = ""
                self._item_widgets[url].refresh()
        self._active = 0
        self._update_counts()

    def _clear_done(self):
        done = [u for u, i in self._items.items()
                if i.status in (DownloadStatus.DONE, DownloadStatus.FAILED,
                                DownloadStatus.CANCELLED)]
        for u in done:
            self._remove_item(u)

    def _update_counts(self):
        total = len(self._items)
        done  = sum(1 for i in self._items.values() if i.status == DownloadStatus.DONE)
        fail  = sum(1 for i in self._items.values() if i.status == DownloadStatus.FAILED)
        act   = sum(1 for i in self._items.values() if i.status == DownloadStatus.DOWNLOADING)
        self.count_label.setText(f"QUEUE  ·  {total} ITEMS")
        self.summary_label.setText(
            f"Done: {done}   Active: {act}   Failed: {fail}   Total: {total}" if total else ""
        )


# ── By Username sub-widget ─────────────────────────────────────────────────────

class _UserWidget(QWidget):
    def __init__(self, tiktok_tab: TikTokTab):
        super().__init__()
        self._tt = tiktok_tab
        self._worker: UserDownloadWorker | None = None
        self._items: dict[str, DownloadItem] = {}
        self._item_widgets: dict[str, DownloadItemWidget] = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(0, 10, 0, 0)

        # Username row
        hint = QLabel("TIKTOK USERNAME")
        hint.setStyleSheet(
            "color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;"
        )

        user_row = QHBoxLayout()
        user_row.setSpacing(8)
        at_label = QLabel("@")
        at_label.setStyleSheet("font-size: 16px; color: #89b4fa; font-weight: 700;")
        at_label.setFixedWidth(16)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("username")
        self.username_input.returnPressed.connect(self._start)

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

        # Control buttons
        ctrl_row = QHBoxLayout()
        self.start_btn = QPushButton("⬇  Fetch & Download All")
        self.start_btn.setObjectName("primary")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self._start)

        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setFixedWidth(76)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)

        ctrl_row.addWidget(self.start_btn)
        ctrl_row.addWidget(self.stop_btn)
        ctrl_row.addStretch()

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #313244;")

        # Progress row
        prog_row = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self.status_label.setMinimumWidth(200)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self.bar.setStyleSheet("""
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

        prog_row.addWidget(self.status_label, 1)
        prog_row.addWidget(self.bar, 2)
        prog_row.addWidget(self.summary_label)

        # Video list
        list_hint = QLabel("VIDEOS")
        list_hint.setObjectName("section")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setSpacing(3)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.addStretch()
        scroll.setWidget(self.list_container)

        root.addWidget(hint)
        root.addLayout(user_row)
        root.addLayout(ctrl_row)
        root.addWidget(divider)
        root.addLayout(prog_row)
        root.addWidget(list_hint)
        root.addWidget(scroll, 1)

    def _start(self):
        username = self.username_input.text().strip().lstrip("@")
        if not username:
            self.status_label.setText("⚠  Please enter a username.")
            return

        for w in list(self._item_widgets.values()):
            self.list_layout.removeWidget(w)
            w.deleteLater()
        self._item_widgets.clear()
        self._items.clear()
        self.bar.setValue(0)
        self.summary_label.setText("")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText(f"Connecting to @{username}…")

        self._worker = UserDownloadWorker(
            username=username,
            save_dir=self._tt.save_dir(),
            max_videos=self.max_spin.value(),
        )
        self._worker.video_found.connect(self._on_video_found)
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(lambda m: self.status_label.setText(m))
        self._worker.video_done.connect(self._on_video_done)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _stop(self):
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
        w = DownloadItemWidget(item)
        self._item_widgets[url] = w
        self.list_layout.insertWidget(self.list_layout.count() - 1, w)

    def _on_progress(self, current: int, total: int):
        if total > 0:
            self.bar.setValue(int(current / total * 100))

    def _on_video_done(self, url: str, ok: bool, msg: str):
        item = self._items.get(url)
        if item:
            item.status = DownloadStatus.DONE if ok else DownloadStatus.FAILED
            item.progress = 100 if ok else 50
            self._item_widgets[url].refresh()
        done = sum(1 for i in self._items.values() if i.status == DownloadStatus.DONE)
        fail = sum(1 for i in self._items.values() if i.status == DownloadStatus.FAILED)
        self.summary_label.setText(
            f"Done: {done}   Failed: {fail}   Total: {len(self._items)}"
        )

    def _on_finished(self, success: int, fail: int):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.bar.setValue(100)
        self.status_label.setText(f"✓  Finished — {success} downloaded, {fail} failed.")
        self.summary_label.setText(
            f"Done: {success}   Failed: {fail}   Total: {len(self._items)}"
        )

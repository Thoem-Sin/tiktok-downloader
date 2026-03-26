import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QScrollArea, QSpinBox,
    QProgressBar, QFrame, QComboBox, QTabWidget, QPlainTextEdit
)
from PySide6.QtCore import Qt

from core.worker import (
    YoutubeDownloadWorker, YoutubePlaylistWorker, YOUTUBE_QUALITIES
)
from core.queue_manager import DownloadItem, DownloadStatus
from ui.widgets import DownloadItemWidget


class YoutubeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_dir = os.path.expanduser("~/Downloads")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 12)

        # ── Quality selector (shared by both sub-tabs)
        quality_row = QHBoxLayout()
        quality_label = QLabel("QUALITY")
        quality_label.setStyleSheet(
            "color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;"
        )
        self.quality_combo = QComboBox()
        for q in YOUTUBE_QUALITIES:
            self.quality_combo.addItem(q)
        self.quality_combo.setFixedWidth(200)
        self.quality_combo.setStyleSheet("""
            QComboBox {
                background: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 6px 12px;
                color: #cdd6f4;
                font-size: 12px;
            }
            QComboBox:focus { border: 1px solid #89b4fa; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView {
                background: #1e1e2e;
                border: 1px solid #313244;
                color: #cdd6f4;
                selection-background-color: #313244;
            }
        """)

        # ── Save folder
        folder_label = QLabel("SAVE FOLDER")
        folder_label.setStyleSheet(
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

        quality_row.addWidget(quality_label)
        quality_row.addWidget(self.quality_combo)
        quality_row.addSpacing(20)
        quality_row.addWidget(folder_label)
        quality_row.addLayout(folder_row, 1)

        # ── Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #313244;")

        # ── Sub-tabs: Single / Playlist
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet("""
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
        """)

        self.single_widget = _SingleVideoWidget(self)
        self.playlist_widget = _PlaylistWidget(self)

        self.sub_tabs.addTab(self.single_widget, "Single Video")
        self.sub_tabs.addTab(self.playlist_widget, "Playlist / Channel")

        root.addLayout(quality_row)
        root.addWidget(divider)
        root.addWidget(self.sub_tabs, 1)

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Folder", self._save_dir)
        if path:
            self._save_dir = path
            self.folder_label.setText(path)
            # propagate to sub-widgets
            self.single_widget.save_dir = path
            self.playlist_widget.save_dir = path

    def quality(self) -> str:
        return self.quality_combo.currentText()

    def save_dir(self) -> str:
        return self._save_dir


# ── Single video sub-widget ────────────────────────────────────────────────────

class _SingleVideoWidget(QWidget):
    def __init__(self, youtube_tab: "YoutubeTab"):
        super().__init__()
        self._yt = youtube_tab
        self.save_dir = youtube_tab._save_dir
        self._items: dict[str, DownloadItem] = {}
        self._item_widgets: dict[str, DownloadItemWidget] = {}
        self._workers: dict[str, YoutubeDownloadWorker] = {}
        self._max_concurrent = 3
        self._active = 0
        self._pending: list[str] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(0, 10, 0, 0)

        # URL input
        hint = QLabel("PASTE YOUTUBE URLS — ONE PER LINE")
        hint.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;")

        self.url_input = QPlainTextEdit()
        self.url_input.setPlaceholderText(
            "https://www.youtube.com/watch?v=...\nhttps://youtu.be/...\n..."
        )
        self.url_input.setFixedHeight(90)

        # Action row
        action_row = QHBoxLayout()
        self.add_btn = QPushButton("＋  Add to Queue")
        self.add_btn.setObjectName("primary")
        self.add_btn.setFixedWidth(130)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_urls)

        self.clear_input_btn = QPushButton("Clear")
        self.clear_input_btn.setFixedWidth(70)
        self.clear_input_btn.setCursor(Qt.PointingHandCursor)
        self.clear_input_btn.clicked.connect(self.url_input.clear)

        action_row.addWidget(self.add_btn)
        action_row.addWidget(self.clear_input_btn)
        action_row.addStretch()

        # Queue header
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

        divider2 = QFrame()
        divider2.setFrameShape(QFrame.HLine)
        divider2.setStyleSheet("color: #313244;")

        root.addWidget(hint)
        root.addWidget(self.url_input)
        root.addLayout(action_row)
        root.addWidget(divider2)
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

        worker = YoutubeDownloadWorker(
            url=url,
            save_dir=self._yt.save_dir(),
            quality=self._yt.quality(),
        )
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
                if i.status in (DownloadStatus.DONE, DownloadStatus.FAILED, DownloadStatus.CANCELLED)]
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


# ── Playlist sub-widget ────────────────────────────────────────────────────────

class _PlaylistWidget(QWidget):
    def __init__(self, youtube_tab: "YoutubeTab"):
        super().__init__()
        self._yt = youtube_tab
        self.save_dir = youtube_tab._save_dir
        self._items: dict[str, DownloadItem] = {}
        self._item_widgets: dict[str, DownloadItemWidget] = {}
        self._worker: YoutubePlaylistWorker | None = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(0, 10, 0, 0)

        # URL row
        hint = QLabel("PLAYLIST OR CHANNEL URL")
        hint.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;")

        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "https://www.youtube.com/playlist?list=...  or  https://www.youtube.com/@channel/videos"
        )
        self.url_input.returnPressed.connect(self._start)

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

        url_row.addWidget(self.url_input, 1)
        url_row.addSpacing(12)
        url_row.addWidget(max_label)
        url_row.addWidget(self.max_spin)
        url_row.addWidget(zero_hint)

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
                    stop:0 #f38ba8, stop:1 #fab387);
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
        root.addLayout(url_row)
        root.addLayout(ctrl_row)
        root.addWidget(divider)
        root.addLayout(prog_row)
        root.addWidget(list_hint)
        root.addWidget(scroll, 1)

    def _start(self):
        url = self.url_input.text().strip()
        if not url:
            self.status_label.setText("⚠  Please enter a URL.")
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
        self.status_label.setText("Fetching playlist…")

        self._worker = YoutubePlaylistWorker(
            url=url,
            save_dir=self._yt.save_dir(),
            quality=self._yt.quality(),
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
        self.status_label.setText("Stopped.")

    def _on_video_found(self, url: str, title: str):
        if url in self._items:
            return
        item = DownloadItem(url=title or url, status=DownloadStatus.PENDING)
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
        self.summary_label.setText(f"Done: {done}   Failed: {fail}   Total: {len(self._items)}")

    def _on_finished(self, success: int, fail: int):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.bar.setValue(100)
        self.status_label.setText(f"✓  Finished — {success} downloaded, {fail} failed.")
        self.summary_label.setText(
            f"Done: {success}   Failed: {fail}   Total: {len(self._items)}"
        )

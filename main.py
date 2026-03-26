from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QLabel, QPushButton, QLineEdit, QPlainTextEdit,
    QFileDialog, QScrollArea, QSpinBox, QFrame, QComboBox, QProgressBar
)
from PySide6.QtCore import Qt, pyqtSignal

from core.license import get_license_status, deactivate
from core.worker import (
    DownloadWorker, UserDownloadWorker, YoutubeDownloadWorker, 
    YoutubePlaylistWorker, YOUTUBE_QUALITIES
)
from core.queue_manager import DownloadItem, DownloadStatus
from ui.widgets import DownloadItemWidget
from ui.style import APP_STYLE
import os


class MainWindow(QMainWindow):
    """Unified downloader with auto-platform detection."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikDL — Universal Video Downloader")
        self.setMinimumSize(960, 680)
        self.resize(1000, 750)
        self.setStyleSheet(APP_STYLE)
        self._save_dir = os.path.expanduser("~/Downloads")
        self._build_ui()
        self._update_license_status()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── License banner ───────────────────────────────────────────────────
        self._lic_banner = QWidget()
        self._lic_banner.setFixedHeight(34)
        self._lic_banner.setStyleSheet(
            "background: #181825; border-bottom: 1px solid #313244;"
        )
        banner_lay = QHBoxLayout(self._lic_banner)
        banner_lay.setContentsMargins(16, 0, 12, 0)
        banner_lay.setSpacing(8)

        self._lic_status_lbl = QLabel("License: checking…")
        self._lic_status_lbl.setStyleSheet(
            "font-size: 11px; color: #6c7086; background: transparent;"
        )
        banner_lay.addWidget(self._lic_status_lbl)
        banner_lay.addStretch()

        deactivate_btn = QPushButton("Deactivate")
        deactivate_btn.setFixedHeight(24)
        deactivate_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #6c7086; border: none; "
            "font-size: 11px; padding: 0 8px; min-height: 0; } "
            "QPushButton:hover { background: transparent; color: #f38ba8; }"
            "QPushButton:pressed { background: transparent; color: #f38ba8; }"
        )
        deactivate_btn.clicked.connect(self._deactivate)
        banner_lay.addWidget(deactivate_btn)
        root.addWidget(self._lic_banner)

        # ── Main content area ────────────────────────────────────────────────
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(16, 14, 16, 12)

        # Save folder picker (shared)
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

        # Divider
        divider1 = QFrame()
        divider1.setFrameShape(QFrame.HLine)
        divider1.setStyleSheet("color: #313244;")

        # ── Input section header ─────────────────────────────────────────────
        input_hint = QLabel("URLS & PROFILES — ONE PER LINE  ·  Auto-detects TikTok, YouTube & Playlists")
        input_hint.setStyleSheet(
            "color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;"
        )

        # URL input with hints
        self.url_input = QPlainTextEdit()
        self.url_input.setPlaceholderText(
            "Paste URLs or profile links:\n"
            "• TikTok: https://www.tiktok.com/@user/video/123456789\n"
            "• TikTok Short: https://vm.tiktok.com/shortlink\n"
            "• TikTok Profile: https://www.tiktok.com/@username\n"
            "• YouTube: https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
            "• YouTube Playlist: https://www.youtube.com/playlist?list=PL..."
        )
        self.url_input.setFixedHeight(100)

        # YouTube quality selector (optional for YouTube)
        quality_row = QHBoxLayout()
        quality_label = QLabel("YOUTUBE QUALITY (if needed):")
        quality_label.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: 600;")
        self.quality_combo = QComboBox()
        for q in YOUTUBE_QUALITIES:
            self.quality_combo.addItem(q)
        self.quality_combo.setFixedWidth(180)
        self.quality_combo.setStyleSheet("""
            QComboBox {
                background: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 6px 12px;
                color: #cdd6f4;
                font-size: 11px;
            }
            QComboBox:focus { border: 1px solid #89b4fa; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView {
                background: #1e1e2e;
                border: 1px solid #313244;
                color: #cdd6f4;
                selection-background-color: #45475a;
            }
        """)
        quality_row.addWidget(quality_label)
        quality_row.addWidget(self.quality_combo)
        quality_row.addStretch()

        # Action buttons
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

        # Divider
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.HLine)
        divider2.setStyleSheet("color: #313244;")

        # ── Queue section ───────────────────────────────────────────────────
        queue_header = QHBoxLayout()
        self.count_label = QLabel("QUEUE  ·  0 ITEMS")
        self.count_label.setObjectName("section")

        self.start_btn = QPushButton("▶ Start All")
        self.start_btn.setObjectName("primary")
        self.start_btn.setFixedWidth(106)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self._start_all)

        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setFixedWidth(76)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self._stop_all)

        clear_done_btn = QPushButton("Clear Done")
        clear_done_btn.setFixedWidth(100)
        clear_done_btn.setCursor(Qt.PointingHandCursor)
        clear_done_btn.clicked.connect(self._clear_done)

        queue_header.addWidget(self.count_label)
        queue_header.addStretch()
        queue_header.addWidget(clear_done_btn)
        queue_header.addWidget(self.stop_btn)
        queue_header.addWidget(self.start_btn)

        # Scroll area for queue items
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

        # Assemble content layout
        content_layout.addWidget(folder_hint)
        content_layout.addLayout(folder_row)
        content_layout.addWidget(divider1)
        content_layout.addWidget(input_hint)
        content_layout.addWidget(self.url_input)
        content_layout.addLayout(quality_row)
        content_layout.addLayout(action_row)
        content_layout.addWidget(divider2)
        content_layout.addLayout(queue_header)
        content_layout.addWidget(scroll, 1)
        content_layout.addWidget(self.summary_label)

        root.addWidget(content, 1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready  ·  Auto-detects platform  ·  Requires yt-dlp and ffmpeg")

        # Initialize download state
        self._items: dict[str, DownloadItem] = {}
        self._item_widgets: dict[str, DownloadItemWidget] = {}
        self._workers: dict[str, DownloadWorker] = {}
        self._max_concurrent = 3
        self._active = 0
        self._pending: list[str] = []

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Folder", self._save_dir)
        if path:
            self._save_dir = path
            self.folder_label.setText(path)

    def save_dir(self) -> str:
        return self._save_dir

    def _detect_platform(self, url: str) -> str:
        """Auto-detect platform from URL."""
        url_lower = url.lower()
        if 'tiktok.com' in url_lower or 'vm.tiktok.com' in url_lower:
            return 'tiktok'
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        return 'unknown'

    def _add_urls(self):
        """Add URLs from input, auto-detecting platform."""
        text = self.url_input.toPlainText().strip()
        if not text:
            return
        
        for line in text.splitlines():
            url = line.strip()
            if url and url not in self._items:
                platform = self._detect_platform(url)
                if platform == 'unknown':
                    continue
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
        self._pending = [u for u in self._pending if u != url]
        self._update_counts()

    def _start_all(self):
        """Start all pending downloads."""
        for url, item in self._items.items():
            if item.status == DownloadStatus.PENDING:
                self._pending.append(url)
        self._process_queue()

    def _process_queue(self):
        """Process queued downloads with concurrency limit."""
        while self._active < self._max_concurrent and self._pending:
            url = self._pending.pop(0)
            if url not in self._items:
                continue
            
            item = self._items[url]
            if item.status != DownloadStatus.PENDING:
                continue
            
            item.status = DownloadStatus.DOWNLOADING
            self._item_widgets[url].refresh()
            
            platform = self._detect_platform(url)
            
            if platform == 'tiktok':
                worker = DownloadWorker(url=url, save_dir=self.save_dir())
            elif platform == 'youtube':
                # Check if URL is playlist
                is_playlist = 'playlist' in url.lower()
                if is_playlist:
                    worker = YoutubePlaylistWorker(
                        url=url, 
                        save_dir=self.save_dir(),
                        quality=self.quality_combo.currentText()
                    )
                else:
                    worker = YoutubeDownloadWorker(
                        url=url,
                        save_dir=self.save_dir(),
                        quality=self.quality_combo.currentText()
                    )
            else:
                item.status = DownloadStatus.FAILED
                item.progress = 0
                self._item_widgets[url].refresh()
                self._process_queue()
                return
            
            self._workers[url] = worker
            worker.progress.connect(lambda p, u=url: self._on_progress(u, p))
            worker.status.connect(lambda s, u=url: self._on_status(u, s))
            worker.finished.connect(lambda ok, msg, u=url: self._on_finished(u, ok, msg))
            self._active += 1
            worker.start()

    def _on_progress(self, url: str, progress: int):
        """Update item progress."""
        if url in self._items:
            self._items[url].progress = progress
            self._item_widgets[url].refresh()

    def _on_status(self, url: str, status: str):
        """Update item status message."""
        if url in self._items:
            self._items[url].speed = status
            self._item_widgets[url].refresh()

    def _on_finished(self, url: str, ok: bool, msg: str):
        """Handle download completion."""
        if url in self._items:
            item = self._items[url]
            item.status = DownloadStatus.DONE if ok else DownloadStatus.FAILED
            item.progress = 100 if ok else 50
            self._item_widgets[url].refresh()
        
        self._workers.pop(url, None)
        self._active -= 1
        self._update_counts()
        self._process_queue()

    def _stop_all(self):
        """Stop all downloads."""
        for worker in self._workers.values():
            worker.cancel()
        self._workers.clear()
        self._pending.clear()
        for url, item in self._items.items():
            if item.status in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING):
                item.status = DownloadStatus.CANCELLED
                item.speed = ""
                self._item_widgets[url].refresh()
        self._active = 0
        self._update_counts()

    def _clear_done(self):
        """Clear finished downloads from queue."""
        done = [u for u, i in self._items.items()
                if i.status in (DownloadStatus.DONE, DownloadStatus.FAILED,
                                DownloadStatus.CANCELLED)]
        for u in done:
            self._remove_item(u)

    def _update_counts(self):
        """Update queue statistics."""
        total = len(self._items)
        done  = sum(1 for i in self._items.values() if i.status == DownloadStatus.DONE)
        fail  = sum(1 for i in self._items.values() if i.status == DownloadStatus.FAILED)
        act   = sum(1 for i in self._items.values() if i.status == DownloadStatus.DOWNLOADING)
        self.count_label.setText(f"QUEUE  ·  {total} ITEMS")
        self.summary_label.setText(
            f"Done: {done}   Active: {act}   Failed: {fail}   Total: {total}" if total else ""
        )

    def _update_license_status(self):
        """Update license status display."""
        status = get_license_status()
        if status["ok"]:
            dl = status["days_left"]
            exp = status["expiry"].strftime("%d %b %Y") if status["expiry"] else "?"
            if dl <= 7:
                color = "#fab387"
                text  = f"⚠️  License expires in {dl} day(s)  ({exp})"
            else:
                color = "#a6e3a1"
                text  = f"✓  License active  ·  {dl} days remaining  ·  Expires {exp}"
        else:
            color = "#f38ba8"
            text  = "✗  License invalid — restart to re-activate"
        self._lic_status_lbl.setText(text)
        self._lic_status_lbl.setStyleSheet(
            f"font-size: 11px; color: {color}; background: transparent;"
        )

    def _deactivate(self):
        """Deactivate license."""
        from PySide6.QtWidgets import QMessageBox
        r = QMessageBox.question(
            self, "Deactivate License",
            "Remove the license from this machine?\n\n"
            "You will need to enter your key again on next startup.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if r == QMessageBox.Yes:
            deactivate()
            QMessageBox.information(
                self, "Deactivated",
                "License removed. The app will close now.\n"
                "Restart TikDL to re-activate."
            )
            import sys
            sys.exit(0)

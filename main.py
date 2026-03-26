from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStatusBar, QLabel, QPushButton, QLineEdit, QScrollArea,
    QFrame, QSpinBox, QProgressBar, QFileDialog, QPlainTextEdit,
    QMessageBox, QComboBox
)
from PySide6.QtCore import Qt

from core.worker import DownloadWorker, UserDownloadWorker
from core.queue_manager import DownloadItem, DownloadStatus
from ui.widgets import DownloadItemWidget
from ui.style import APP_STYLE
from core.license import get_license_status, deactivate

import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikDL — Video Downloader")
        self.setMinimumSize(900, 700)
        self.resize(1000, 750)
        self.setStyleSheet(APP_STYLE)
        
        self._save_dir = os.path.expanduser("~/Downloads")
        self._items = {}
        self._worker = None
        self._current_mode = "urls"
        
        self._build_ui()
        self._update_license_status()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ──────────────────────────────────────────────────────────────────────
        # License Banner
        # ──────────────────────────────────────────────────────────────────────
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

        # ──────────────────────────────────────────────────────────────────────
        # Main Content
        # ──────────────────────────────────────────────────────────────────────
        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setSpacing(14)
        content_lay.setContentsMargins(16, 16, 16, 12)

        # ──────────────────────────────────────────────────────────────────────
        # Save Folder Section
        # ──────────────────────────────────────────────────────────────────────
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
        browse_btn.setFixedWidth(100)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(folder_icon)
        folder_row.addWidget(self.folder_label, 1)
        folder_row.addWidget(browse_btn)

        # ──────────────────────────────────────────────────────────────────────
        # Divider
        # ──────────────────────────────────────────────────────────────────────
        divider1 = QFrame()
        divider1.setFrameShape(QFrame.HLine)
        divider1.setStyleSheet("color: #313244;")

        # ──────────────────────────────────────────────────────────────────────
        # Input Mode Selection
        # ──────────────────────────────────────────────────────────────────────
        mode_hint = QLabel("INPUT MODE")
        mode_hint.setStyleSheet(
            "color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;"
        )

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_row.addWidget(QLabel("Select input type:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "URLs (Auto-detect platform)",
            "Profile URLs",
            "Usernames"
        ])
        self.mode_combo.setFixedWidth(250)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()

        # ──────────────────────────────────────────────────────────────────────
        # Input Section
        # ──────────────────────────────────────────────────────────────────────
        input_hint = QLabel("INPUT")
        input_hint.setStyleSheet(
            "color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;"
        )

        self.input_label = QLabel("Enter URLs (one per line) — Auto-detects TikTok, YouTube, Instagram, etc.")
        self.input_label.setStyleSheet("color: #a6adc8; font-size: 11px;")

        self.input_text = QPlainTextEdit()
        self.input_text.setPlaceholderText(
            "Paste URLs here, one per line\n\n"
            "Examples:\n"
            "  https://www.tiktok.com/@username/video/123456789\n"
            "  https://youtu.be/dQw4w9WgXcQ\n"
            "  https://www.instagram.com/p/ABC123/"
        )
        self.input_text.setFixedHeight(120)
        self.input_text.setStyleSheet(
            "color: #cdd6f4; background: #313244; border: 1px solid #45475a; "
            "border-radius: 6px; padding: 8px; selection-background-color: #89b4fa;"
        )

        # ──────────────────────────────────────────────────────────────────────
        # Download Options
        # ──────────────────────────────────────────────────────────────────────
        options_hint = QLabel("OPTIONS")
        options_hint.setStyleSheet(
            "color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;"
        )

        options_row = QHBoxLayout()
        options_row.setSpacing(16)

        # Video quality
        quality_lbl = QLabel("Quality:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Best", "High (720p)", "Medium (480p)", "Low (360p)"])
        self.quality_combo.setFixedWidth(150)
        options_row.addWidget(quality_lbl)
        options_row.addWidget(self.quality_combo)

        # Audio only
        self.audio_btn = QPushButton("Audio Only")
        self.audio_btn.setCheckable(True)
        self.audio_btn.setFixedWidth(100)
        self.audio_btn.setStyleSheet(
            "QPushButton { background: #313244; color: #a6adc8; border: 1px solid #45475a; "
            "border-radius: 6px; padding: 6px; } "
            "QPushButton:checked { background: #89b4fa; color: #1e1e2e; } "
            "QPushButton:hover { background: #45475a; }"
        )
        options_row.addWidget(self.audio_btn)

        # Threads
        threads_lbl = QLabel("Threads:")
        self.threads_spin = QSpinBox()
        self.threads_spin.setMinimum(1)
        self.threads_spin.setMaximum(8)
        self.threads_spin.setValue(2)
        self.threads_spin.setFixedWidth(60)
        options_row.addWidget(threads_lbl)
        options_row.addWidget(self.threads_spin)

        options_row.addStretch()

        # ──────────────────────────────────────────────────────────────────────
        # Download Buttons
        # ──────────────────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.download_btn = QPushButton("↓ Download")
        self.download_btn.setFixedHeight(36)
        self.download_btn.setFixedWidth(120)
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setStyleSheet(
            "QPushButton { background: #89b4fa; color: #1e1e2e; border: none; "
            "border-radius: 6px; font-weight: 600; } "
            "QPushButton:hover { background: #a6d7ff; } "
            "QPushButton:pressed { background: #7aa6da; }"
        )
        self.download_btn.clicked.connect(self._start_download)

        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setFixedHeight(36)
        self.pause_btn.setFixedWidth(100)
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._pause_download)

        self.clear_btn = QPushButton("🗑 Clear")
        self.clear_btn.setFixedHeight(36)
        self.clear_btn.setFixedWidth(100)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear_input)

        btn_row.addWidget(self.download_btn)
        btn_row.addWidget(self.pause_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()

        # ──────────────────────────────────────────────────────────────────────
        # Divider
        # ──────────────────────────────────────────────────────────────────────
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.HLine)
        divider2.setStyleSheet("color: #313244;")

        # ──────────────────────────────────────────────────────────────────────
        # Download Queue
        # ──────────────────────────────────────────────────────────────────────
        queue_hint = QLabel("DOWNLOAD QUEUE")
        queue_hint.setStyleSheet(
            "color: #6c7086; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;"
        )

        # Scroll area for download items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; } "
            "QScrollBar:vertical { background: #313244; width: 8px; } "
            "QScrollBar::handle:vertical { background: #45475a; border-radius: 4px; }"
        )

        self.queue_container = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setSpacing(8)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.addStretch()

        scroll.setWidget(self.queue_container)

        # ──────────────────────────────────────────────────────────────────────
        # Assembly
        # ──────────────────────────────────────────────────────────────────────
        content_lay.addWidget(folder_hint)
        content_lay.addLayout(folder_row)
        content_lay.addWidget(divider1)
        content_lay.addWidget(mode_hint)
        content_lay.addLayout(mode_row)
        content_lay.addWidget(input_hint)
        content_lay.addWidget(self.input_label)
        content_lay.addWidget(self.input_text)
        content_lay.addWidget(options_hint)
        content_lay.addLayout(options_row)
        content_lay.addLayout(btn_row)
        content_lay.addWidget(divider2)
        content_lay.addWidget(queue_hint)
        content_lay.addWidget(scroll, 1)

        root.addWidget(content, 1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — Auto-detects platform from URL")

    def _on_mode_changed(self, mode_text):
        """Update input label based on selected mode."""
        if "Auto-detect" in mode_text:
            self._current_mode = "urls"
            self.input_label.setText(
                "Enter URLs (one per line) — Auto-detects TikTok, YouTube, Instagram, etc."
            )
            self.input_text.setPlaceholderText(
                "Paste URLs here, one per line\n\n"
                "Examples:\n"
                "  https://www.tiktok.com/@username/video/123456789\n"
                "  https://youtu.be/dQw4w9WgXcQ\n"
                "  https://www.instagram.com/p/ABC123/"
            )
        elif "Profile" in mode_text:
            self._current_mode = "profiles"
            self.input_label.setText(
                "Enter profile/channel URLs (one per line) — Downloads all videos from profile"
            )
            self.input_text.setPlaceholderText(
                "Paste profile URLs here, one per line\n\n"
                "Examples:\n"
                "  https://www.tiktok.com/@username\n"
                "  https://www.youtube.com/@channelname\n"
                "  https://www.instagram.com/username/"
            )
        else:  # Usernames
            self._current_mode = "usernames"
            self.input_label.setText(
                "Enter usernames (one per line) — Downloads all videos from user"
            )
            self.input_text.setPlaceholderText(
                "Paste usernames here, one per line\n\n"
                "Examples:\n"
                "  username123\n"
                "  @tiktok_creator\n"
                "  yt_channel_name"
            )

    def _detect_platform(self, url: str) -> str:
        """Auto-detect platform from URL."""
        url_lower = url.lower()
        
        if "tiktok.com" in url_lower or "vt.tiktok.com" in url_lower:
            return "TikTok"
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "YouTube"
        elif "instagram.com" in url_lower or "instagr.am" in url_lower:
            return "Instagram"
        elif "twitter.com" in url_lower or "x.com" in url_lower:
            return "Twitter/X"
        elif "twitch.tv" in url_lower:
            return "Twitch"
        elif "reddit.com" in url_lower:
            return "Reddit"
        elif "facebook.com" in url_lower or "fb.watch" in url_lower:
            return "Facebook"
        else:
            return "Unknown"

    def _start_download(self):
        """Start downloading from input."""
        content = self.input_text.toPlainText().strip()
        
        if not content:
            QMessageBox.warning(self, "No Input", "Please enter at least one URL or username.")
            return

        lines = [line.strip() for line in content.split("\n") if line.strip()]
        
        if not lines:
            QMessageBox.warning(self, "No Input", "Please enter at least one valid URL or username.")
            return

        for line in lines:
            platform = self._detect_platform(line) if self._current_mode == "urls" else "Multi"
            item_id = f"{platform}_{len(self._items)}"
            
            item = DownloadItem(
                id=item_id,
                url=line,
                platform=platform,
                status=DownloadStatus.QUEUED
            )
            
            self._items[item_id] = item
            
            # Add to UI
            widget = DownloadItemWidget(item)
            # Remove the stretch if it exists
            if self.queue_layout.count() > 0:
                spacer = self.queue_layout.takeAt(self.queue_layout.count() - 1)
            self.queue_layout.addWidget(widget)
            self.queue_layout.addStretch()

        self.download_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.status_bar.showMessage(f"Downloading {len(lines)} item(s)...")

    def _pause_download(self):
        """Pause current download."""
        if self._worker:
            self._worker.pause()
        self.pause_btn.setEnabled(False)
        self.download_btn.setEnabled(True)
        self.status_bar.showMessage("Paused")

    def _clear_input(self):
        """Clear input text."""
        self.input_text.clear()
        self.input_text.setFocus()

    def _browse_folder(self):
        """Browse for save folder."""
        path = QFileDialog.getExistingDirectory(self, "Select Save Folder", self._save_dir)
        if path:
            self._save_dir = path
            self.folder_label.setText(path)

    def _update_license_status(self):
        """Update license status banner."""
        status = get_license_status()
        if status["ok"]:
            dl = status["days_left"]
            exp = status["expiry"].strftime("%d %b %Y") if status["expiry"] else "?"
            if dl <= 7:
                color = "#fab387"
                text = f"⚠️  License expires in {dl} day(s)  ({exp})"
            else:
                color = "#a6e3a1"
                text = f"✓  License active  ·  {dl} days remaining  ·  Expires {exp}"
        else:
            color = "#f38ba8"
            text = "✗  License invalid — restart to re-activate"
        
        self._lic_status_lbl.setText(text)
        self._lic_status_lbl.setStyleSheet(
            f"font-size: 11px; color: {color}; background: transparent;"
        )

    def _deactivate(self):
        """Deactivate license."""
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

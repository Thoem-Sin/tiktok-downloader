from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QTabWidget, QStatusBar, QLabel, QHBoxLayout, QPushButton
)
from PySide6.QtCore import Qt

from ui.style import APP_STYLE
from ui.tiktok_tab import TikTokTab
from ui.youtube_tab import YoutubeTab
from core.license import get_license_status, deactivate


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikDL — Video Downloader")
        self.setMinimumSize(860, 640)
        self.resize(960, 700)
        self.setStyleSheet(APP_STYLE)
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

        # ── Tabs ─────────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tiktok_tab  = TikTokTab()
        self.youtube_tab = YoutubeTab()

        self.tabs.addTab(self.tiktok_tab,  "  TikTok  ")
        self.tabs.addTab(self.youtube_tab, "  YouTube  ")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            "Ready  ·  Requires yt-dlp and ffmpeg  ·  pip install yt-dlp"
        )

        root.addWidget(self.tabs)

    def _update_license_status(self):
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

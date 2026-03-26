"""
ui/activation_dialog.py  —  License activation dialog for TikDL.
"""

import webbrowser
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QApplication, QWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QFont

from core.license import (
    get_machine_id, activate, get_bot_deep_link, BOT_USERNAME
)

# ── Palette ────────────────────────────────────────────────────────────────────
BG       = "#1e1e2e"
BG1      = "#181825"
BG2      = "#11111b"
BORDER   = "#313244"
BORDER2  = "#45475a"
TEXT     = "#cdd6f4"
SUBTEXT  = "#6c7086"
BLUE     = "#89b4fa"
GREEN    = "#a6e3a1"
RED      = "#f38ba8"
PEACH    = "#fab387"
YELLOW   = "#f9e2af"

STYLE = f"""
QDialog  {{ background: {BG}; }}
QWidget  {{ background: {BG}; color: {TEXT};
            font-family: "Segoe UI", Arial, sans-serif; font-size: 13px; }}
QLabel   {{ background: transparent; color: {TEXT}; }}

QLineEdit {{
    background: {BG1};
    border: 1px solid {BORDER2};
    border-radius: 8px;
    padding: 0 14px;
    color: {TEXT};
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    min-height: 40px;
}}
QLineEdit:focus      {{ border: 1px solid {BLUE}; }}
QLineEdit:read-only  {{
    background: {BG2};
    color: {BLUE};
    border: 1px solid {BORDER};
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 1px;
}}

QPushButton {{
    background: {BORDER};
    color: {TEXT};
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
    min-height: 40px;
    padding: 0 20px;
}}
QPushButton:hover    {{ background: {BORDER2}; color: {TEXT}; }}
QPushButton:pressed  {{ background: #585b70;  color: {TEXT}; }}
QPushButton:disabled {{ background: {BORDER}; color: {SUBTEXT}; }}

QPushButton#activate {{
    background: {BLUE};
    color: #11111b;
    font-weight: 700;
    font-size: 14px;
    border-radius: 8px;
    min-height: 44px;
}}
QPushButton#activate:hover    {{ background: #a8caff; color: #11111b; }}
QPushButton#activate:pressed  {{ background: #74c7ec; color: #11111b; }}
QPushButton#activate:disabled {{
    background: {BORDER};
    color: {SUBTEXT};
}}

QPushButton#tg {{
    background: transparent;
    color: {SUBTEXT};
    border: 1px solid {BORDER2};
    border-radius: 8px;
    font-size: 12px;
    font-weight: 500;
    min-height: 38px;
}}
QPushButton#tg:hover {{ background: {BORDER}; color: {TEXT}; border-color: {BORDER2}; }}

QPushButton#lnk {{
    background: transparent;
    color: {SUBTEXT};
    border: none;
    font-size: 11px;
    min-height: 20px;
    padding: 0;
}}
QPushButton#lnk:hover {{ color: {RED}; background: transparent; }}

QFrame#sep {{
    background: {BORDER};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}
"""


def _sep() -> QFrame:
    f = QFrame()
    f.setObjectName("sep")
    f.setFrameShape(QFrame.HLine)
    return f


def _cap(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(
        f"font-size: 10px; font-weight: 700; color: {SUBTEXT}; letter-spacing: 1.4px;"
    )
    return l


# ── Activation Dialog ─────────────────────────────────────────────────────────

class ActivationDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TikDL — Activate License")
        self.setFixedWidth(460)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setStyleSheet(STYLE)
        self._machine_id = get_machine_id()
        self._build_ui()
        self.adjustSize()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top header panel ────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet(f"background: {BG1}; border-bottom: 1px solid {BORDER};")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(32, 24, 32, 22)
        hl.setSpacing(6)

        icon = QLabel("⬇")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            f"font-size: 28px; color: {BLUE}; background: transparent;"
        )
        hl.addWidget(icon)

        title = QLabel("License Activation")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 800; color: {TEXT}; background: transparent;"
        )
        hl.addWidget(title)

        sub = QLabel("A valid license is required to use TikDL.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(
            f"font-size: 12px; color: {SUBTEXT}; background: transparent;"
        )
        hl.addWidget(sub)
        root.addWidget(header)

        # ── Body ────────────────────────────────────────────────────────────
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(32, 22, 32, 24)
        bl.setSpacing(16)

        # Machine ID block
        mid_block = QVBoxLayout()
        mid_block.setSpacing(6)
        mid_block.addWidget(_cap("Your Machine ID"))

        mid_row = QHBoxLayout()
        mid_row.setSpacing(8)

        self._mid_box = QLineEdit(self._machine_id)
        self._mid_box.setReadOnly(True)
        self._mid_box.setFixedHeight(42)
        mid_row.addWidget(self._mid_box, 1)

        copy_btn = QPushButton("Copy")
        copy_btn.setFixedWidth(80)
        copy_btn.setFixedHeight(42)
        copy_btn.clicked.connect(self._copy_mid)
        mid_row.addWidget(copy_btn)
        mid_block.addLayout(mid_row)

        hint = QLabel("Send this ID to the Telegram bot to receive your license key.")
        hint.setStyleSheet(f"font-size: 11px; color: {SUBTEXT};")
        hint.setWordWrap(True)
        mid_block.addWidget(hint)
        bl.addLayout(mid_block)

        bl.addWidget(_sep())

        # License key block
        key_block = QVBoxLayout()
        key_block.setSpacing(6)
        key_block.addWidget(_cap("License Key"))

        key_row = QHBoxLayout()
        key_row.setSpacing(8)

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("TIKDL-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")
        self._key_input.setFixedHeight(42)
        self._key_input.textChanged.connect(self._on_key_changed)
        self._key_input.returnPressed.connect(self._activate)
        key_row.addWidget(self._key_input, 1)

        paste_btn = QPushButton("Paste")
        paste_btn.setFixedWidth(80)
        paste_btn.setFixedHeight(42)
        paste_btn.clicked.connect(self._paste_key)
        key_row.addWidget(paste_btn)
        key_block.addLayout(key_row)
        bl.addLayout(key_block)

        # Activate button
        self._activate_btn = QPushButton("Activate License")
        self._activate_btn.setObjectName("activate")
        self._activate_btn.setFixedHeight(44)
        self._activate_btn.setEnabled(False)
        self._activate_btn.clicked.connect(self._activate)
        bl.addWidget(self._activate_btn)

        # Status label — only visible after clicking Activate
        self._status_lbl = QLabel("")
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setStyleSheet(f"font-size: 12px; color: {SUBTEXT};")
        self._status_lbl.setMinimumHeight(18)
        bl.addWidget(self._status_lbl)

        bl.addWidget(_sep())

        # Telegram button
        tg_btn = QPushButton(f"🔗  Open @{BOT_USERNAME} on Telegram")
        tg_btn.setObjectName("tg")
        tg_btn.setFixedHeight(38)
        tg_btn.clicked.connect(self._open_bot)
        bl.addWidget(tg_btn)

        # Exit link
        exit_btn = QPushButton("Exit without activating")
        exit_btn.setObjectName("lnk")
        exit_btn.clicked.connect(self.reject)
        bl.addWidget(exit_btn, alignment=Qt.AlignCenter)

        root.addWidget(body)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _copy_mid(self):
        QGuiApplication.clipboard().setText(self._machine_id)
        self._set_status("✓  Machine ID copied to clipboard!", GREEN)
        QTimer.singleShot(2000, lambda: self._set_status("", SUBTEXT))

    def _open_bot(self):
        webbrowser.open(get_bot_deep_link(self._machine_id))

    def _paste_key(self):
        txt = QGuiApplication.clipboard().text().strip()
        if txt:
            self._key_input.setText(txt)

    def _on_key_changed(self, text: str):
        clean = text.strip().upper().replace("-", "").replace(" ", "")
        self._activate_btn.setEnabled(len(clean) == 35 and clean.startswith("TIKDL"))
        self._set_status("", SUBTEXT)

    def _set_status(self, msg: str, color: str):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"font-size: 12px; color: {color};")

    def _activate(self):
        key = self._key_input.text().strip()
        if not key:
            return
        self._activate_btn.setEnabled(False)
        self._activate_btn.setText("Validating…")
        self._set_status("Checking with server…", BLUE)
        QApplication.processEvents()

        ok, msg = activate(key)

        if ok:
            self._set_status(f"✓  {msg}", GREEN)
            self._activate_btn.setText("✓  Activated!")
            QTimer.singleShot(1200, self.accept)
        else:
            self._set_status(f"✗  {msg}", RED)
            self._activate_btn.setEnabled(True)
            self._activate_btn.setText("Activate License")


# ── License Problem Dialog ────────────────────────────────────────────────────

class LicenseExpiredDialog(QDialog):

    def __init__(self, status: dict, parent=None):
        super().__init__(parent)
        self._machine_id = get_machine_id()
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setStyleSheet(STYLE)

        sc     = status.get("status_code", "")
        expiry = status.get("expiry")
        dl     = status.get("days_left", 0)
        reason = status.get("reason", "Your license is no longer valid.")

        if sc == "revoked":
            self._icon, self._color = "🚫", RED
            self._title = "License Revoked"
            self._msg   = "This license has been revoked by the administrator.\nContact support or purchase a new license."
            self._date  = None
            self.setWindowTitle("TikDL — License Revoked")
        elif sc == "expired" or (expiry and dl <= 0):
            self._icon, self._color = "⏰", PEACH
            self._title = "License Expired"
            self._msg   = "Your license has expired.\nPlease renew to continue using TikDL."
            self._date  = f"Expired: {expiry.strftime('%d %b %Y')}" if expiry else None
            self.setWindowTitle("TikDL — License Expired")
        elif sc == "machine_mismatch":
            self._icon, self._color = "💻", YELLOW
            self._title = "Wrong Machine"
            self._msg   = "This key is registered to a different machine.\nPlease use the key issued for this machine."
            self._date  = None
            self.setWindowTitle("TikDL — License Error")
        elif sc == "not_found":
            self._icon, self._color = "❓", YELLOW
            self._title = "License Not Found"
            self._msg   = "This key was not found in the database.\nPlease check the key or contact the administrator."
            self._date  = None
            self.setWindowTitle("TikDL — License Not Found")
        else:
            self._icon, self._color = "⚠️", RED
            self._title = "License Invalid"
            self._msg   = reason
            self._date  = f"Expired: {expiry.strftime('%d %b %Y')}" if expiry else None
            self.setWindowTitle("TikDL — License Invalid")

        self.setFixedWidth(420)
        self._build_ui()
        self.adjustSize()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(f"background: {BG1}; border-bottom: 1px solid {BORDER};")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(32, 24, 32, 20)
        hl.setSpacing(8)

        icon = QLabel(self._icon)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 36px; background: transparent;")
        hl.addWidget(icon)

        title = QLabel(self._title)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 800; color: {self._color}; background: transparent;"
        )
        hl.addWidget(title)
        root.addWidget(header)

        # Body
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(32, 20, 32, 24)
        bl.setSpacing(12)

        msg = QLabel(self._msg)
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"font-size: 13px; color: {SUBTEXT}; line-height: 1.5;")
        bl.addWidget(msg)

        if self._date:
            dl = QLabel(self._date)
            dl.setAlignment(Qt.AlignCenter)
            dl.setStyleSheet(f"font-size: 12px; color: {PEACH}; font-weight: 700;")
            bl.addWidget(dl)

        bl.addWidget(_sep())

        renew = QPushButton(f"Renew on @{BOT_USERNAME}")
        renew.setObjectName("activate")
        renew.setFixedHeight(42)
        renew.clicked.connect(
            lambda: webbrowser.open(get_bot_deep_link(self._machine_id))
        )
        bl.addWidget(renew)

        enter = QPushButton("Enter New License Key")
        enter.setFixedHeight(38)
        enter.clicked.connect(self.accept)
        bl.addWidget(enter)

        ex = QPushButton("Exit")
        ex.setObjectName("lnk")
        ex.clicked.connect(self.reject)
        bl.addWidget(ex, alignment=Qt.AlignCenter)

        root.addWidget(body)


# ── License Expiring Soon Dialog ──────────────────────────────────────────────

class LicenseExpiringDialog(QDialog):
    """Shown when license is valid but expiring within 7 days."""

    def __init__(self, days_left: int, expiry, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TikDL — License Expiring Soon")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setStyleSheet(STYLE)
        self._machine_id = get_machine_id()
        self._days_left  = days_left
        self._expiry     = expiry
        self.setFixedWidth(420)
        self._build_ui()
        self.adjustSize()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet(f"background: {BG1}; border-bottom: 1px solid {BORDER};")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(32, 24, 32, 20)
        hl.setSpacing(8)

        icon = QLabel("⚠️")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 36px; background: transparent;")
        hl.addWidget(icon)

        title = QLabel("License Expiring Soon")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 800; color: {YELLOW}; background: transparent;"
        )
        hl.addWidget(title)
        root.addWidget(header)

        # ── Body ────────────────────────────────────────────────────────────
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(32, 20, 32, 24)
        bl.setSpacing(12)

        exp_str = self._expiry.strftime('%d %b %Y') if self._expiry else "soon"

        # Days remaining badge
        badge = QLabel(f"{self._days_left} day{'s' if self._days_left != 1 else ''} remaining")
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"font-size: 24px; font-weight: 800; color: {YELLOW};"
        )
        bl.addWidget(badge)

        exp_lbl = QLabel(f"Expires on  {exp_str}")
        exp_lbl.setAlignment(Qt.AlignCenter)
        exp_lbl.setStyleSheet(f"font-size: 13px; color: {PEACH}; font-weight: 600;")
        bl.addWidget(exp_lbl)

        msg = QLabel("Please renew your license before it expires\nto continue using TikDL without interruption.")
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"font-size: 12px; color: {SUBTEXT};")
        bl.addWidget(msg)

        bl.addWidget(_sep())

        # Renew button
        renew = QPushButton(f"Renew on @{BOT_USERNAME}")
        renew.setObjectName("activate")
        renew.setFixedHeight(42)
        renew.clicked.connect(
            lambda: webbrowser.open(get_bot_deep_link(self._machine_id))
        )
        bl.addWidget(renew)

        # Continue button
        cont = QPushButton("Continue Anyway")
        cont.setFixedHeight(38)
        cont.clicked.connect(self.accept)
        bl.addWidget(cont)

        root.addWidget(body)

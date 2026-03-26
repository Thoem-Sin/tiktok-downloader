APP_STYLE = """
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #1e1e2e;
}

/* ── Tabs ─────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 8px;
    background: #181825;
    padding: 4px;
}

QTabBar::tab {
    background: #1e1e2e;
    color: #6c7086;
    padding: 8px 22px;
    border: none;
    border-radius: 6px;
    margin-right: 4px;
    font-weight: 600;
    font-size: 12px;
}

QTabBar::tab:selected {
    background: #313244;
    color: #cdd6f4;
}

QTabBar::tab:hover:!selected {
    background: #252740;
    color: #a6adc8;
}

/* ── Inputs ───────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 8px 12px;
    color: #cdd6f4;
    selection-background-color: #585b70;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #89b4fa;
}

QLineEdit::placeholder, QTextEdit::placeholder {
    color: #585b70;
}

/* ── Buttons ──────────────────────────────────── */
QPushButton {
    background: #313244;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 0 14px;
    font-weight: 600;
    font-size: 13px;
    min-height: 30px;
    max-height: 34px;
}

QPushButton:hover {
    background: #45475a;
    color: #cdd6f4;
}

QPushButton:pressed {
    background: #585b70;
    color: #cdd6f4;
}

QPushButton:disabled {
    background: #252538;
    color: #45475a;
}

QPushButton#primary {
    background: #89b4fa;
    color: #1e1e2e;
    font-weight: 700;
    min-height: 30px;
    max-height: 34px;
    padding: 0 16px;
}

QPushButton#primary:hover {
    background: #b4befe;
    color: #1e1e2e;
}

QPushButton#primary:pressed {
    background: #74c7ec;
    color: #1e1e2e;
}

QPushButton#primary:disabled {
    background: #313244;
    color: #45475a;
}

QPushButton#danger {
    background: #f38ba8;
    color: #1e1e2e;
    font-weight: 700;
    min-height: 30px;
    max-height: 34px;
    padding: 0 14px;
}

QPushButton#danger:hover {
    background: #eba0ac;
    color: #1e1e2e;
}

QPushButton#danger:pressed {
    background: #f2cdcd;
    color: #1e1e2e;
}

QPushButton#success {
    background: #a6e3a1;
    color: #1e1e2e;
    font-weight: 700;
}

QPushButton#success:hover {
    background: #94e2d5;
    color: #1e1e2e;
}

QPushButton#warning {
    background: #f9e2af;
    color: #1e1e2e;
    font-weight: 700;
}

QPushButton#warning:hover {
    background: #fab387;
    color: #1e1e2e;
}

QPushButton#ghost {
    background: transparent;
    color: #a6adc8;
    border: 1px solid #45475a;
}

QPushButton#ghost:hover {
    background: #313244;
    color: #cdd6f4;
}

QPushButton#ghost:pressed {
    background: #45475a;
    color: #cdd6f4;
}

/* ── SpinBox ──────────────────────────────────── */
QSpinBox {
    background: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 6px 10px;
    color: #cdd6f4;
}

QSpinBox:focus {
    border: 1px solid #89b4fa;
}

/* ── CheckBox ─────────────────────────────────── */
QCheckBox {
    spacing: 8px;
    color: #cdd6f4;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid #585b70;
    background: #181825;
}

QCheckBox::indicator:checked {
    background: #89b4fa;
    border-color: #89b4fa;
    image: none;
}

QCheckBox::indicator:hover {
    border-color: #89b4fa;
}

/* ── ScrollArea ───────────────────────────────── */
QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    background: #181825;
    width: 8px;
    margin: 0;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #45475a;
    min-height: 30px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #585b70;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Labels ───────────────────────────────────── */
QLabel#title {
    font-size: 22px;
    font-weight: 700;
    color: #89b4fa;
    letter-spacing: 1px;
}

QLabel#subtitle {
    font-size: 12px;
    color: #6c7086;
}

QLabel#section {
    font-size: 11px;
    font-weight: 700;
    color: #6c7086;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

/* ── Status bar ───────────────────────────────── */
QStatusBar {
    background: #181825;
    color: #6c7086;
    font-size: 11px;
    border-top: 1px solid #313244;
}

/* ── Separator ────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    color: #313244;
}

/* ── GroupBox ─────────────────────────────────── */
QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 8px;
    font-weight: 600;
    color: #a6adc8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 12px;
}

/* ── ToolTip ──────────────────────────────────── */
QToolTip {
    background: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}
"""

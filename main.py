import sys
from PySide6.QtWidgets import QApplication

from core.license import get_license_status
from ui.activation_dialog import (
    ActivationDialog, LicenseExpiredDialog, LicenseExpiringDialog
)
from ui.main_window import MainWindow


def _run_license_check(app: QApplication) -> bool:
    while True:
        status = get_license_status()

        # No license saved → activation screen
        if not status["activated"]:
            dlg = ActivationDialog()
            if dlg.exec() != ActivationDialog.Accepted:
                return False
            continue

        # License invalid (expired, revoked, wrong machine, not found)
        if not status["ok"]:
            dlg = LicenseExpiredDialog(status)
            result = dlg.exec()
            if result == LicenseExpiredDialog.Accepted:
                act_dlg = ActivationDialog()
                if act_dlg.exec() != ActivationDialog.Accepted:
                    return False
                continue
            else:
                return False

        # License valid — warn if expiring within 7 days
        days_left = status["days_left"]
        if days_left <= 7:
            expiry = status["expiry"]
            warn = LicenseExpiringDialog(days_left, expiry)
            warn.exec()   # user can dismiss and continue either way

        return True


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TikDL")
    app.setOrganizationName("TikDL")

    if not _run_license_check(app):
        sys.exit(0)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

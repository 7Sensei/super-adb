from PySide6.QtWidgets import QFileDialog, QInputDialog, QLineEdit, QWidget


def choose_apk_file(parent: QWidget) -> str:
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "Pilih File APK",
        "",
        "APK Files (*.apk)",
    )
    return file_path


def ask_package_name(parent: QWidget) -> str | None:
    value, accepted = QInputDialog.getText(
        parent,
        "Uninstall App",
        "Masukkan Package Name:",
        QLineEdit.EchoMode.Normal,
    )
    return value if accepted and value else None


def ask_device_ip(parent: QWidget) -> str | None:
    value, accepted = QInputDialog.getText(
        parent,
        "Connect Wireless",
        "Masukkan IP HP:",
        QLineEdit.EchoMode.Normal,
    )
    return value if accepted and value else None

from PySide6.QtWidgets import QWidget

from super_adb.ui.dialogs import ask_device_ip
from super_adb.ui.pages.actions import ActionDefinition, ActionPage
from super_adb.ui.theme.manager import ThemeManager
from super_adb.viewmodels.main_viewmodel import MainViewModel


class NetworkPage(ActionPage):
    def __init__(
        self,
        viewmodel: MainViewModel,
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
    ) -> None:
        actions: list[ActionDefinition] = [
            (
                "enable-tcpip",
                "Aktifkan Port TCP/IP 5555",
                "Aktifkan koneksi ADB melalui jaringan pada port 5555.",
                "plug-zap.svg",
                viewmodel.enable_tcpip,
            ),
            (
                "connect-wireless",
                "Connect ke IP HP",
                "Masukkan alamat IP perangkat untuk koneksi wireless.",
                "wifi.svg",
                lambda: self._connect_wireless(viewmodel),
            ),
            (
                "disconnect-devices",
                "Disconnect Semua",
                "Putuskan seluruh koneksi ADB wireless.",
                "circle-alert.svg",
                viewmodel.disconnect_devices,
            ),
        ]
        super().__init__(actions, theme_manager, parent)

    def _connect_wireless(self, viewmodel: MainViewModel) -> None:
        ip_address = ask_device_ip(self)
        if ip_address:
            viewmodel.connect_wireless(ip_address)

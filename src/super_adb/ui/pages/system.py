from PySide6.QtWidgets import QWidget

from super_adb.ui.pages.actions import ActionDefinition, ActionPage
from super_adb.ui.theme.manager import ThemeManager
from super_adb.viewmodels.main_viewmodel import MainViewModel


class SystemPage(ActionPage):
    def __init__(
        self,
        viewmodel: MainViewModel,
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
    ) -> None:
        actions: list[ActionDefinition] = [
            (
                "check-devices",
                "Cek Perangkat Terhubung",
                "Perbarui daftar perangkat ADB yang terhubung.",
                "refresh-cw.svg",
                viewmodel.check_devices,
                "default",
            ),
            (
                "basic-info",
                "Info Perangkat Dasar",
                "Tampilkan merek, model, dan nama produk.",
                "smartphone.svg",
                viewmodel.show_basic_info,
                "default",
            ),
            (
                "hardware",
                "Cek Hardware Lengkap",
                "Tampilkan versi Android, prosesor, layar, dan RAM.",
                "cpu.svg",
                viewmodel.check_hardware,
                "primary",
            ),
            (
                "battery",
                "Status Baterai",
                "Tampilkan informasi baterai perangkat.",
                "battery-charging.svg",
                viewmodel.show_battery_status,
                "default",
            ),
            (
                "reboot",
                "Reboot Normal",
                "Mulai ulang perangkat Android yang dipilih.",
                "power.svg",
                viewmodel.reboot_device,
                "danger",
            ),
        ]
        super().__init__(actions, theme_manager, parent)

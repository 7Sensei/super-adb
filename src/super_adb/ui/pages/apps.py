from PySide6.QtWidgets import QWidget

from super_adb.ui.dialogs import ask_package_name, choose_apk_file
from super_adb.ui.pages.actions import ActionDefinition, ActionPage
from super_adb.ui.theme.manager import ThemeManager
from super_adb.viewmodels.main_viewmodel import MainViewModel


class AppsPage(ActionPage):
    def __init__(
        self,
        viewmodel: MainViewModel,
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
    ) -> None:
        actions: list[ActionDefinition] = [
            (
                "install-apk",
                "Pilih & Install APK",
                "Pilih file APK dari komputer untuk dipasang.",
                "download.svg",
                lambda: self._install_apk(viewmodel),
            ),
            (
                "list-apps",
                "List Semua Aplikasi",
                "Tampilkan daftar package pada perangkat.",
                "package.svg",
                viewmodel.list_apps,
            ),
            (
                "uninstall-app",
                "Uninstall Aplikasi",
                "Masukkan nama package aplikasi yang akan dihapus.",
                "trash-2.svg",
                lambda: self._uninstall_app(viewmodel),
            ),
        ]
        super().__init__(actions, theme_manager, parent)

    def _install_apk(self, viewmodel: MainViewModel) -> None:
        file_path = choose_apk_file(self)
        if file_path:
            viewmodel.install_apk(file_path)

    def _uninstall_app(self, viewmodel: MainViewModel) -> None:
        package_name = ask_package_name(self)
        if package_name:
            viewmodel.uninstall_app(package_name)

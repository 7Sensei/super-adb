from __future__ import annotations

from concurrent.futures import Executor, Future, ThreadPoolExecutor

from super_adb.models.device import Device
from super_adb.services.adb_service import AdbService
from super_adb.services.errors import AdbError
from super_adb.viewmodels.base import Observable, Signal, UiDispatcher


class MainViewModel:
    def __init__(
        self,
        adb_service: AdbService,
        dispatcher: UiDispatcher,
        executor: Executor | None = None,
    ) -> None:
        self._adb_service = adb_service
        self._dispatcher = dispatcher
        self._executor = (
            executor
            if executor is not None
            else ThreadPoolExecutor(max_workers=1, thread_name_prefix="super-adb")
        )
        self._owns_executor = executor is None

        self.devices: Observable[list[Device]] = Observable([])
        self.selected_device: Observable[Device | None] = Observable(None)
        self.is_busy: Observable[bool] = Observable(False)
        self.status: Observable[str] = Observable("Siap")
        self.log: Signal[str] = Signal()

    def check_devices(self) -> None:
        self._run_command(["adb", "devices"], update_devices=True)

    def show_basic_info(self) -> None:
        self._run_command(
            [
                "adb",
                "shell",
                "echo 'Merek:' $(getprop ro.product.brand) "
                "'| Model:' $(getprop ro.product.model) "
                "'| Nama:' $(getprop ro.product.name)",
            ]
        )

    def check_hardware(self) -> None:
        self._run_command(
            [
                "adb",
                "shell",
                "echo '=== PLATFORM & OS ===';"
                "echo 'Android Ver : ' $(getprop ro.build.version.release);"
                "echo 'API Level   : ' $(getprop ro.build.version.sdk);"
                "echo 'Chipset     : ' $(getprop ro.board.platform);"
                "echo 'CPU Arch    : ' $(getprop ro.product.cpu.abi);"
                "echo ' ';"
                "echo '=== LAYAR (DISPLAY) ===';"
                "wm size;"
                "wm density;"
                "echo ' ';"
                "echo '=== MEMORI (RAM) ===';"
                "cat /proc/meminfo | grep MemTotal | awk "
                "'{printf \"Total RAM   : %.2f GB\\n\", $2/1024/1024}';",
            ]
        )

    def show_battery_status(self) -> None:
        self._run_command(["adb", "shell", "dumpsys", "battery"])

    def reboot_device(self) -> None:
        self._run_command(["adb", "reboot"])

    def list_apps(self) -> None:
        self._run_command(["adb", "shell", "pm", "list", "packages"])

    def install_apk(self, file_path: str) -> None:
        if file_path and self._is_safe_argument(file_path, "Path APK"):
            self._run_command(["adb", "install", file_path])

    def uninstall_app(self, package_name: str) -> None:
        if package_name and self._is_safe_argument(package_name, "Package name"):
            self._run_command(["adb", "uninstall", package_name])

    def enable_tcpip(self) -> None:
        self._run_command(["adb", "tcpip", "5555"])

    def connect_wireless(self, ip_address: str) -> None:
        if ip_address and self._is_safe_argument(ip_address, "IP"):
            self._run_command(["adb", "connect", ip_address])

    def disconnect_devices(self) -> None:
        self._run_command(["adb", "disconnect"])

    def close(self) -> None:
        if self._owns_executor:
            self._executor.shutdown(wait=False, cancel_futures=True)

    def _run_command(self, command: list[str], update_devices: bool = False) -> None:
        self.is_busy.value = True
        self.status.value = "Menjalankan perintah ADB"
        self.log.emit(f"\n> Menjalankan: {' '.join(command)}")
        self._executor.submit(self._execute, command).add_done_callback(
            lambda future: self._dispatcher.post(lambda: self._finish(future, update_devices))
        )

    def _is_safe_argument(self, value: str, label: str) -> bool:
        if value.lstrip().startswith("-"):
            message = f"{label} tidak boleh diawali dengan '-'."
            self.status.value = message
            self.log.emit(f"Error: {message}")
            return False
        return True

    def _execute(self, command: list[str]) -> str:
        return self._adb_service.execute(
            command, lambda line: self._dispatcher.post(lambda: self.log.emit(line))
        )

    def _finish(self, future: Future[str], update_devices: bool) -> None:
        try:
            output = future.result()
        except AdbError as error:
            self.status.value = str(error)
            self.log.emit(f"Error: {error}")
        except Exception as error:
            self.status.value = f"Kesalahan sistem: {error}"
            self.log.emit(f"Terjadi kesalahan sistem: {error}")
        else:
            self.status.value = "Selesai"
            if update_devices:
                self._update_devices(output)
        finally:
            self.is_busy.value = False
            self.log.emit("-" * 50)

    def _update_devices(self, output: str) -> None:
        devices = []
        for line in output.splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[1] in {
                "device",
                "offline",
                "unauthorized",
                "bootloader",
                "recovery",
                "sideload",
            }:
                devices.append(Device(serial=fields[0], state=fields[1]))

        self.devices.value = devices
        current = self.selected_device.value
        if current is not None:
            self.selected_device.value = next(
                (device for device in devices if device.serial == current.serial), None
            )

from __future__ import annotations

import threading
from concurrent.futures import Executor, Future, ThreadPoolExecutor

from super_adb.models.device import Device
from super_adb.models.device_info import DeviceInfo
from super_adb.models.log_entry import LogEntry, LogKind
from super_adb.services.adb_service import AdbService
from super_adb.services.errors import AdbError
from super_adb.viewmodels.base import Observable, Signal
from super_adb.viewmodels.ports import UiDispatcher


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
        self.devices: Observable[list[Device]] = Observable([])
        self.selected_serial: Observable[str | None] = Observable(None)
        self.device_info: Observable[DeviceInfo | None] = Observable(None)
        self.can_run_device_commands: Observable[bool] = Observable(False)
        self.is_busy: Observable[bool] = Observable(False)
        self.status: Observable[str] = Observable("Siap")
        self.log_line: Signal[LogEntry] = Signal()
        self.log: Signal[str] = Signal()
        self.lifecycle_event: Signal[str] = Signal()

        self._poll_lock = threading.Lock()
        self._poll_in_flight = False

    def check_devices(self) -> None:
        self._run_command(["adb", "devices"], update_devices=True)

    def select_device(self, serial: str | None) -> None:
        candidate = next((device for device in self.devices.value if device.serial == serial), None)
        selected = candidate.serial if candidate is not None else None
        if selected == self.selected_serial.value:
            return
        self.selected_serial.value = selected
        self._refresh_can_run()
        if self.can_run_device_commands.value:
            self.refresh_device_info()
        else:
            self.device_info.value = None

    def poll_devices(self) -> None:
        with self._poll_lock:
            if self._poll_in_flight:
                return
            self._poll_in_flight = True
        future = self._executor.submit(self._fetch_devices)

        def finish_poll(completed: Future[list[Device]]) -> None:
            self._dispatcher.post(lambda: self._finish_poll(completed))

        future.add_done_callback(finish_poll)

    def refresh_device_info(self) -> None:
        serial = self.selected_serial.value
        if serial is None or not self.can_run_device_commands.value:
            self.device_info.value = None
            return
        future = self._executor.submit(self._adb_service.get_device_info, serial)
        future.add_done_callback(
            lambda completed: self._dispatcher.post(
                lambda: self._finish_device_info(completed, serial)
            )
        )

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
        self.lifecycle_event.emit("reboot")
        self._run_command(["adb", "reboot"])

    def reset_adb(self) -> None:
        if self.is_busy.value:
            message = "Reset ADB tidak dapat dilakukan saat operasi lain sedang berjalan."
            self.status.value = message
            self._emit_log(message, "error")
            return
        self.lifecycle_event.emit("reset")
        self.is_busy.value = True
        self.status.value = "Mereset ADB"
        self._emit_log("> Menjalankan: adb kill-server && adb start-server", "command")
        future = self._executor.submit(self._reset_adb_server)
        future.add_done_callback(
            lambda completed: self._dispatcher.post(
                lambda: self._finish_reset_adb(completed)
            )
        )

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
        try:
            self._adb_service.close()
        finally:
            self._executor.shutdown(wait=False, cancel_futures=True)

    def _run_command(self, command: list[str], update_devices: bool = False) -> None:
        device_command = self._requires_device(command)
        if device_command:
            serial = self.selected_serial.value
            if serial is None or not self.can_run_device_commands.value:
                message = "Pilih perangkat ADB berstatus device terlebih dahulu."
                self.status.value = message
                self._emit_log(message, "error")
                return
            command = ["adb", "-s", serial, *command[1:]]

        self.is_busy.value = True
        self.status.value = "Menjalankan perintah ADB"
        self._emit_log(f"> Menjalankan: {' '.join(command)}", "command")
        self._executor.submit(self._execute, command).add_done_callback(
            lambda future: self._dispatcher.post(lambda: self._finish(future, update_devices))
        )

    @staticmethod
    def _requires_device(command: list[str]) -> bool:
        return command[1:2] not in (
            ["devices"],
            ["connect"],
            ["disconnect"],
            ["start-server"],
            ["kill-server"],
            ["version"],
        )

    def _is_safe_argument(self, value: str, label: str) -> bool:
        if value.lstrip().startswith("-"):
            message = f"{label} tidak boleh diawali dengan '-'."
            self.status.value = message
            self._emit_log(message, "error")
            return False
        return True

    def _execute(self, command: list[str]) -> str:
        def on_line(line: str) -> None:
            self._dispatcher.post(lambda: self._emit_log(line, "output"))

        return self._adb_service.execute(command, on_line)

    def _reset_adb_server(self) -> str:
        def on_line(line: str) -> None:
            self._dispatcher.post(lambda: self._emit_log(line, "output"))

        stopped = self._adb_service.execute(["adb", "kill-server"], on_line)
        started = self._adb_service.execute(["adb", "start-server"], on_line)
        return "\n".join((stopped, started))

    def _finish_reset_adb(self, future: Future[str]) -> None:
        succeeded = False
        try:
            future.result()
        except AdbError as error:
            self.status.value = str(error)
            self._emit_log(f"Error: {error}", "error")
        except Exception as error:
            self.status.value = f"Kesalahan sistem: {error}"
            self._emit_log(f"Terjadi kesalahan sistem: {error}", "error")
        else:
            self.status.value = "Selesai"
            succeeded = True
        finally:
            self.is_busy.value = False
            self._emit_log("-" * 50, "info")
        if succeeded:
            self.poll_devices()

    def _fetch_devices(self) -> list[Device]:
        output = self._adb_service.execute(["adb", "devices"], lambda line: None)
        return self._parse_devices(output)

    def _finish(
        self,
        future: Future[str],
        update_devices: bool,
    ) -> None:
        try:
            output = future.result()
        except AdbError as error:
            self.status.value = str(error)
            self._emit_log(f"Error: {error}", "error")
        except Exception as error:
            self.status.value = f"Kesalahan sistem: {error}"
            self._emit_log(f"Terjadi kesalahan sistem: {error}", "error")
        else:
            self.status.value = "Selesai"
            if update_devices:
                self._update_devices(self._parse_devices(output))
        finally:
            self.is_busy.value = False
            self._emit_log("-" * 50, "info")

    def _finish_poll(self, future: Future[list[Device]]) -> None:
        try:
            devices = future.result()
        except AdbError:
            return
        finally:
            with self._poll_lock:
                self._poll_in_flight = False
        self._update_devices(devices)

    def _finish_device_info(self, future: Future[DeviceInfo], serial: str) -> None:
        try:
            info = future.result()
        except Exception as error:
            self._emit_log(f"Gagal membaca detail perangkat: {error}", "error")
            return
        if self.selected_serial.value == serial:
            self.device_info.value = info

    def _update_devices(self, devices: list[Device]) -> None:
        previous_devices = self.devices.value
        if devices != previous_devices:
            self.devices.value = devices

        previous_serial = self.selected_serial.value
        available_serials = {device.serial for device in devices}
        selected = previous_serial if previous_serial in available_serials else None
        online_devices = [device for device in devices if device.state == "device"]
        if selected is None and len(online_devices) == 1:
            selected = online_devices[0].serial
        if selected != previous_serial:
            self.selected_serial.value = selected

        self._refresh_can_run()
        selected_device = next((device for device in devices if device.serial == selected), None)
        previous_selected_device = next(
            (device for device in previous_devices if device.serial == selected), None
        )
        if selected_device is None or selected_device.state != "device":
            self.device_info.value = None
        elif (
            selected != previous_serial
            or selected_device != previous_selected_device
            or self.device_info.value is None
        ):
            self.refresh_device_info()

    def _refresh_can_run(self) -> None:
        selected = self.selected_serial.value
        self.can_run_device_commands.value = any(
            device.serial == selected and device.state == "device" for device in self.devices.value
        )

    @staticmethod
    def _parse_devices(output: str) -> list[Device]:
        valid_states = {
            "device",
            "offline",
            "unauthorized",
            "bootloader",
            "recovery",
            "sideload",
        }
        devices = []
        for line in output.splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[1] in valid_states:
                devices.append(Device(serial=fields[0], state=fields[1]))
        return devices

    def _emit_log(self, text: str, kind: LogKind) -> None:
        self.log_line.emit(LogEntry(kind=kind, text=text))
        self.log.emit(text)

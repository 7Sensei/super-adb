from unittest.mock import patch

from super_adb.models.device_info import DeviceInfo
from super_adb.services.adb_service import SubprocessAdbService
from super_adb.services.errors import AdbError


def test_get_device_info_parses_all_available_fields_and_uses_per_call_timeout() -> None:
    outputs = {
        "ro.product.brand": "Brand X",
        "ro.product.model": "Model Y",
        "ro.product.name": "product-y",
        "ro.build.version.release": "11",
        "ro.build.version.sdk": "30",
        "ro.board.platform": "chipset-z",
        "ro.product.cpu.abi": "arm64-v8a",
        "size": "Physical size: 1080x2340\nOverride size: 720x1600\n",
        "density": "Physical density: 420\nOverride density: 320\n",
        "/proc/meminfo": "MemTotal: 8388608 kB\n",
        "battery": "level: 75\nstatus: 2\n",
    }
    calls: list[tuple[list[str], float | None]] = []

    def execute(command: list[str], on_line, timeout: float | None = None) -> str:
        calls.append((command, timeout))
        return outputs[command[-1]]

    service = SubprocessAdbService()
    with patch.object(service, "execute", side_effect=execute):
        info = service.get_device_info("serial-1")

    assert info == DeviceInfo(
        serial="serial-1",
        state="device",
        brand="Brand X",
        model="Model Y",
        product_name="product-y",
        android_version="11",
        api_level=30,
        chipset="chipset-z",
        cpu_abi="arm64-v8a",
        screen_w=720,
        screen_h=1600,
        density=320,
        ram_gb=8.0,
        battery_level=75,
        charging=True,
    )
    assert len(calls) == 11
    assert all(command[:3] == ["adb", "-s", "serial-1"] for command, _ in calls)
    assert all(timeout == 8.0 for _, timeout in calls)


def test_get_device_info_keeps_other_fields_when_one_command_fails() -> None:
    def execute(command: list[str], on_line, timeout: float | None = None) -> str:
        if command[-1] == "density":
            raise AdbError("wm density unavailable")
        return {
            "ro.product.brand": "Brand X",
            "ro.product.model": "Model Y",
            "ro.product.name": "product-y",
            "ro.build.version.release": "11",
            "ro.build.version.sdk": "30",
            "ro.board.platform": "chipset-z",
            "ro.product.cpu.abi": "arm64-v8a",
            "size": "Physical size: 1080x2340\n",
            "/proc/meminfo": "MemTotal: 8388608 kB\n",
            "battery": "level: 75\nstatus: 5\n",
        }[command[-1]]

    service = SubprocessAdbService()
    with patch.object(service, "execute", side_effect=execute):
        info = service.get_device_info("serial-1")

    assert info.brand == "Brand X"
    assert info.model == "Model Y"
    assert info.density is None
    assert info.battery_level == 75
    assert info.charging is False

# Super-ADB

Super-ADB is a desktop interface for common Android Debug Bridge (ADB) actions.

## Run from a checkout

```powershell
python -m pip install -e ".[dev]"
python -m super_adb
```

There is no `main.py` launcher: this project uses a `src/` layout, so install
the package before running it as a module.

ADB (Android Platform Tools) must be installed and available on `PATH` when an
ADB action is run. The application reports a clear error if it cannot find ADB.

## Available actions

- View connected-device output, basic device properties, hardware details, and
  battery status; reboot a device.
- List, install, and uninstall applications.
- Enable ADB over TCP/IP, connect to a device IP, and disconnect devices.
- Change the interface font.

import threading

from PySide6.QtWidgets import QApplication

from super_adb.ui.icons import load_icon
from super_adb.ui.qt_dispatcher import QtDispatcher
from super_adb.ui.theme.manager import ThemeManager
from super_adb.ui.theme.tokens import THEMES


def test_qt_dispatcher_runs_worker_callbacks_on_the_gui_thread(qtbot) -> None:
    dispatcher = QtDispatcher()
    gui_thread = threading.get_ident()
    observed: list[int] = []
    worker = threading.Thread(
        target=lambda: dispatcher.post(lambda: observed.append(threading.get_ident()))
    )

    worker.start()
    worker.join()
    qtbot.waitUntil(lambda: len(observed) == 1)

    assert observed == [gui_thread]
    dispatcher.close()


def test_theme_manager_applies_tokens_and_emits_theme_changed(qapp: QApplication) -> None:
    manager = ThemeManager(qapp)
    observed = []
    manager.themeChanged.connect(observed.append)

    manager.apply("light")

    assert manager.tokens == THEMES["light"]
    assert manager.tokens.bg in qapp.styleSheet()
    assert observed == [THEMES["light"]]


def test_lucide_icon_loader_returns_a_valid_icon(qapp: QApplication) -> None:
    icon = load_icon("monitor.svg", THEMES["dark"].accent, size=24)

    assert not icon.isNull()

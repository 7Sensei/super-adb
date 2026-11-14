import os
import sys
import threading
from pathlib import Path

import pytest
from PySide6.QtGui import QFont, QFontDatabase, QFontInfo, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QListWidget,
    QPlainTextEdit,
    QScrollArea,
    QWidget,
)

from super_adb.ui.icons import load_icon
from super_adb.ui.qt_dispatcher import QtDispatcher
from super_adb.ui.theme.manager import ThemeManager
from super_adb.ui.theme.tokens import THEMES
from super_adb.ui.widgets.log_panel import LogPanel


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


def test_qt_dispatcher_drops_queued_callbacks_after_close(qtbot) -> None:
    dispatcher = QtDispatcher()
    observed: list[str] = []

    dispatcher.post(lambda: observed.append("late"))
    dispatcher.close()
    qtbot.wait(20)

    assert observed == []


def test_theme_manager_applies_tokens_and_emits_theme_changed(qapp: QApplication) -> None:
    manager = ThemeManager(qapp)
    observed = []
    manager.themeChanged.connect(observed.append)

    manager.apply("light")

    assert manager.tokens == THEMES["light"]
    assert manager.tokens.bg in qapp.styleSheet()
    assert observed == [THEMES["light"]]


def test_list_and_combo_popup_use_theme_tokens(qapp: QApplication) -> None:
    manager = ThemeManager(qapp)
    manager.apply("dark")
    list_widget = QListWidget()
    combo = QComboBox()
    popup = combo.view()

    for mode in ("dark", "light"):
        manager.apply(mode)
        tokens = THEMES[mode]
        for widget in (list_widget, popup):
            palette = widget.palette()
            assert palette.color(QPalette.ColorRole.Base).name() == tokens.surface.lower()
            assert palette.color(QPalette.ColorRole.Text).name() == tokens.text.lower()
            assert palette.color(QPalette.ColorRole.Highlight).name() == tokens.accent.lower()
        stylesheet = qapp.styleSheet()
        assert "$" not in stylesheet
        assert tokens.surface in stylesheet
        assert "QAbstractItemView::item:selected" in stylesheet


def test_scrollbar_corner_is_transparent(qapp: QApplication) -> None:
    manager = ThemeManager(qapp)
    manager.apply("dark")

    stylesheet = qapp.styleSheet()
    assert "QAbstractScrollArea::corner" in stylesheet
    assert "background: transparent;" in stylesheet


def test_lucide_icon_loader_returns_a_valid_icon(qapp: QApplication) -> None:
    icon = load_icon("monitor.svg", THEMES["dark"].accent, size=24)

    assert not icon.isNull()


def test_scrollbars_are_thin_and_only_visible_when_content_overflows(
    qtbot,
    qapp: QApplication,
) -> None:
    manager = ThemeManager(qapp)
    manager.apply("dark")

    area = QScrollArea()
    area.setWidgetResizable(True)
    area.resize(200, 120)
    content = QWidget()
    content.setMinimumSize(400, 500)
    area.setWidget(content)
    qtbot.addWidget(area)
    area.show()
    qtbot.wait(20)

    assert area.verticalScrollBar().width() == 8
    assert area.horizontalScrollBar().height() == 8
    assert area.verticalScrollBar().isVisible()
    assert area.horizontalScrollBar().isVisible()

    area.setWidget(QWidget())
    qtbot.wait(20)
    assert not area.verticalScrollBar().isVisible()
    assert not area.horizontalScrollBar().isVisible()


def test_log_panel_uses_fixed_pitch_font_and_wrap_toggle(
    qtbot,
    qapp: QApplication,
) -> None:
    if sys.platform == "win32" and not QFontDatabase.hasFamily("Consolas"):
        windows_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        QFontDatabase.addApplicationFont(str(windows_dir / "Fonts" / "consola.ttf"))
    fixed_pitch_families = [
        family
        for family in QFontDatabase.families()
        if QFontInfo(QFont(family)).fixedPitch()
    ]
    if not fixed_pitch_families:
        pytest.skip("Tidak ada font fixed-pitch pada sistem.")
    manager = ThemeManager(qapp, "Arial")
    panel = LogPanel()
    qtbot.addWidget(panel)

    assert QFontInfo(panel.output.font()).fixedPitch()
    assert panel.output.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth
    assert panel.wrap_toggle.isChecked()

    manager.set_font_family("Arial")
    manager.apply("light")
    assert manager.font_family == "Arial"
    assert QFontInfo(panel.output.font()).fixedPitch()
    assert 'font-family: "Arial"' in qapp.styleSheet()
    assert 'QPlainTextEdit#logOutput' in qapp.styleSheet()
    panel.wrap_toggle.setChecked(False)
    assert panel.output.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap
    panel.wrap_toggle.setChecked(True)
    assert panel.output.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth


def test_theme_manager_rejects_unavailable_font_without_changing_stylesheet(
    qapp: QApplication,
) -> None:
    manager = ThemeManager(qapp)
    manager.apply("dark")
    previous_family = manager.font_family
    previous_stylesheet = qapp.styleSheet()

    with pytest.raises(ValueError, match="Keluarga font tidak tersedia"):
        manager.set_font_family("SuperAdbUnavailableFont")

    assert manager.font_family == previous_family
    assert qapp.styleSheet() == previous_stylesheet

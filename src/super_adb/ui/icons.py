from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_ICON_DIRECTORY = Path(__file__).parent / "assets" / "icons"


def load_icon(name: str, color: str, size: int = 20) -> QIcon:
    if not name or Path(name).name != name or not name.endswith(".svg"):
        raise ValueError(f"Nama ikon tidak valid: {name!r}")
    svg_path = _ICON_DIRECTORY / name
    svg = svg_path.read_text(encoding="utf-8").replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    if not renderer.isValid():
        raise ValueError(f"SVG ikon tidak valid: {svg_path}")

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

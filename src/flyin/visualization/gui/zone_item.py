"""Graphical representation of one Fly-in zone."""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from flyin.domain.zone import Zone, ZoneType

RADIUS = 24.0
_MARGIN = 20.0
_TYPE_COLORS = {
    ZoneType.NORMAL: QColor("#4a90d9"),
    ZoneType.PRIORITY: QColor("#2ecc71"),
    ZoneType.RESTRICTED: QColor("#e74c3c"),
    ZoneType.BLOCKED: QColor("#7f8c8d"),
}


class ZoneItem(QGraphicsItem):
    """Renders one zone as a labeled, colored circle.

    Positioned at the zone's scene coordinates; drawing happens in the
    item's local coordinate space, centered on (0, 0).
    """

    def __init__(
        self,
        zone: Zone,
        center_x: float,
        center_y: float,
        is_start: bool,
        is_goal: bool,
    ) -> None:
        """Initialize the item and place it at its scene position.

        Args:
            zone: The zone this item represents.
            center_x: Scene X coordinate of the zone's center.
            center_y: Scene Y coordinate of the zone's center.
            is_start: Whether this is the map's start zone.
            is_goal: Whether this is the map's end zone.
        """
        super().__init__()
        self._zone = zone
        self._is_start = is_start
        self._is_goal = is_goal
        self.setPos(center_x, center_y)
        self.setZValue(0)

    def boundingRect(self) -> QRectF:
        """Return the item's local bounding box, including its labels."""
        size = 2 * (RADIUS + _MARGIN)
        return QRectF(-RADIUS - _MARGIN, -RADIUS - _MARGIN, size, size)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """Draw the zone's circle, border, name, and capacity/role labels."""
        painter.setBrush(QBrush(self._fill_color()))
        pen = QPen(QColor("#0f172a"), 3.0 if self._is_landmark() else 1.5)
        if self._is_landmark():
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawEllipse(QRectF(-RADIUS, -RADIUS, 2 * RADIUS, 2 * RADIUS))

        name_font = QFont()
        name_font.setPointSize(8)
        name_font.setBold(True)
        painter.setFont(name_font)
        painter.setPen(QColor("#0f172a"))
        painter.drawText(
            QRectF(-RADIUS, -6, 2 * RADIUS, 12),
            Qt.AlignmentFlag.AlignCenter,
            self._zone.name,
        )

        caption = self._caption()
        if caption:
            small_font = QFont()
            small_font.setPointSize(7)
            painter.setFont(small_font)
            painter.setPen(QColor("#e2e8f0"))
            painter.drawText(
                QRectF(-RADIUS - _MARGIN, RADIUS + 3, 2 * (RADIUS + _MARGIN), 14),
                Qt.AlignmentFlag.AlignCenter,
                caption,
            )

    def _is_landmark(self) -> bool:
        return self._is_start or self._is_goal

    def _caption(self) -> str:
        parts = []
        if self._is_start:
            parts.append("START")
        if self._is_goal:
            parts.append("END")
        if self._zone.max_drones > 1:
            parts.append(f"cap {self._zone.max_drones}")
        return " / ".join(parts)

    def _fill_color(self) -> QColor:
        if self._zone.color:
            candidate = QColor(self._zone.color)
            if candidate.isValid():
                return candidate
        return _TYPE_COLORS.get(self._zone.zone_type, _TYPE_COLORS[ZoneType.NORMAL])

"""Graphical representation of one drone."""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

RADIUS = 8.0
_COLORS = (
    QColor("#ef4444"),
    QColor("#22c55e"),
    QColor("#eab308"),
    QColor("#3b82f6"),
    QColor("#a855f7"),
    QColor("#14b8a6"),
)


class DroneItem(QGraphicsItem):
    """Renders one drone as a small colored dot labeled with its id.

    The item's scene position *is* the drone's displayed center; moving
    a drone is just `setPos(point)`, which `GraphScene` drives from
    `Simulation` data without ever touching the simulation itself.
    """

    def __init__(self, drone_id: int) -> None:
        """Initialize the item, colored deterministically by drone id."""
        super().__init__()
        self._drone_id = drone_id
        self.setZValue(10)

    def boundingRect(self) -> QRectF:
        """Return the item's local bounding box, including its id label."""
        return QRectF(-RADIUS - 2, -RADIUS - 14, 2 * RADIUS + 4, 2 * RADIUS + 16)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """Draw the drone's dot and its id label above it."""
        color = _COLORS[(self._drone_id - 1) % len(_COLORS)]
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor("#0f172a"), 1))
        painter.drawEllipse(QRectF(-RADIUS, -RADIUS, 2 * RADIUS, 2 * RADIUS))

        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#f8fafc"))
        painter.drawText(
            QRectF(-16, -RADIUS - 14, 32, 12),
            Qt.AlignmentFlag.AlignCenter,
            f"D{self._drone_id}",
        )

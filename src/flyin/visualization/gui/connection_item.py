"""Graphical representation of one connection between two zones."""

from PySide6.QtCore import Qt, QLineF, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from flyin.domain.connection import Connection

_LINE_COLOR = QColor("#475569")
_LABEL_COLOR = QColor("#facc15")


class ConnectionItem(QGraphicsItem):
    """Renders one bidirectional connection as a line, with a capacity label.

    Drawn in scene coordinates directly (the item's own position stays
    at the scene origin), since it spans two independently-positioned
    zones rather than being centered on a single point.
    """

    def __init__(
        self,
        connection: Connection,
        source_pos: QPointF,
        destination_pos: QPointF,
    ) -> None:
        """Initialize the item spanning the two zones it connects.

        Args:
            connection: The connection this item represents.
            source_pos: Scene position of the connection's source zone.
            destination_pos: Scene position of its destination zone.
        """
        super().__init__()
        self._connection = connection
        self._line = QLineF(source_pos, destination_pos)
        self.setZValue(-1)

    def boundingRect(self) -> QRectF:
        """Return a bounding box covering both endpoints."""
        return QRectF(self._line.p1(), self._line.p2()).normalized().adjusted(
            -18, -18, 18, 18,
        )

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """Draw the connection line and, if its capacity > 1, a label."""
        painter.setPen(QPen(_LINE_COLOR, 2))
        painter.drawLine(self._line)

        if self._connection.max_capacity > 1:
            midpoint = self._line.center()
            font = QFont()
            font.setPointSize(7)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(_LABEL_COLOR)
            painter.drawText(
                QRectF(midpoint.x() - 16, midpoint.y() - 8, 32, 16),
                Qt.AlignmentFlag.AlignCenter,
                f"x{self._connection.max_capacity}",
            )

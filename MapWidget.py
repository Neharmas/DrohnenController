from PyQt6.QtWidgets import QWidget, QGraphicsScene
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygon, QPolygonF
from PyQt6.QtCore import Qt, QPointF, QRect

class MapWidgetNew(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drone_position = [0.0, 0.0]
        self.field_of_view = [[0,0],[0,0],[0,0],[0,0]]
        self.drone_size = 10
        self.flown_path = []
        self.setSceneRect(-5000, -5000, 10000, 10000)

    def update_drone_position(self, position):
        self.drone_position = position
        if len(self.flown_path) > 0 and self.flown_path[-1] != self.drone_position:
            self.flown_path.append(self.drone_position)
        self.update()

    def update_field_of_view(self, field_of_view):
        self.field_of_view = field_of_view

    def drawBackground(self, painter, rect):
        grid_size = 20
        pen = QPen(QColor(200, 200, 200))
        pen.setWidth(1)
        painter.setPen(pen)

        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        right = int(rect.right())
        bottom = int(rect.bottom())

        # Draws vertical gridlines
        for x in range(left, right, grid_size):
            painter.drawLine(x, int(rect.top()), x, bottom)
        # Draws horizontal gridlines
        for y in range(top, bottom, grid_size):
            painter.drawLine(int(rect.left()), y, right, y)

        painter.setBrush(QColor(255, 255, 0))
        polypoints = [QPointF(0, 0), QPointF(20, -40), QPointF(-20, -40)]

        for point in polypoints:
            point.setX(self.drone_position[0] + point.x())
            point.setY(self.drone_position[1] + point.y())
        painter.drawPolygon(QPolygonF(polypoints))

        # Draw drone position
        painter.setBrush(QColor(255, 0, 0))
        visual_drone_position = [int(self.drone_position[0] - self.drone_size/2), int(self.drone_position[1] - self.drone_size/2)]
        painter.drawEllipse(visual_drone_position[0], visual_drone_position[1], self.drone_size, self.drone_size)


class MapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.grid_size = 50  # Abstand zwischen Linien (Pixel)
        self.drone_position = QPointF(150, 150)  # Startposition (Mitte)
        self.path = []  # Liste der letzten Drohnenpositionen

        self.field_of_view = [[20,20], [40,20], [20, 40], [40, 40]]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 30, 30))  # dunkler Hintergrund

        # Gitterlinien
        pen = QPen(QColor(80, 80, 80))
        pen.setWidth(1)
        painter.setPen(pen)

        width = self.width()
        height = self.height()

        # vertikale Linien
        for x in range(0, width + 1, self.grid_size):
            painter.drawLine(x, 0, x, height)

        # horizontale Linien
        for y in range(0, height + 1, self.grid_size):
            painter.drawLine(0, y, width, y)

        # Flugweg zeichnen
        if len(self.path) > 1:
            pen.setColor(QColor(0, 255, 255))
            pen.setWidth(2)
            painter.setPen(pen)
            for i in range(1, len(self.path)):
                painter.drawLine(self.path[i-1], self.path[i])

        # View Rect
        rect = QRect(int(self.drone_position.x()) - 20, int(self.drone_position.y()) - 40, 40, 20)
        painter.drawRect(rect)
        #painter.fillRect(rect, QColor(255, 255, 0, 200))

        painter.drawArc(rect, 30 * 16, 120 * 16)

        # Drohne zeichnen
        painter.setBrush(QColor(255, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        radius = 6
        painter.drawEllipse(self.drone_position, radius, radius)

    def update_drone_position(self, dx, dy):
        """Verschiebt die Drohne auf der Karte (z. B. bei Steuerung)"""
        new_x = self.drone_position.x() + dx
        new_y = self.drone_position.y() + dy

        # Begrenzung innerhalb des Widgets
        new_x = max(0, min(self.width(), new_x))
        new_y = max(0, min(self.height(), new_y))

        self.drone_position = QPointF(new_x, new_y)
        self.path.append(QPointF(new_x, new_y))
        self.update()

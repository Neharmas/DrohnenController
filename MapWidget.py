from PyQt6.QtWidgets import QGraphicsScene, QGraphicsLineItem, QGraphicsView
from PyQt6.QtGui import QColor, QPen, QPolygonF
from PyQt6.QtCore import QPointF

class MapWidgetNew(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drone_position = [0.0, 0.0]
        self.field_of_view = [{'x': 0, 'y': 0},
                              {'x': 0, 'y': 0},
                              {'x': 0, 'y': 0},
                              {'x': 0, 'y': 0}]
        self.grid_size = 10
        self.drone_size = 10
        self.animal_size = 10
        self.flown_path = []
        self.animal_position = None
        self.setSceneRect(-5000, -5000, 10000, 10000)

    def update_drone_position(self, position):
        self.drone_position = position
        if len(self.flown_path) > 0 and self.flown_path[-1] != self.drone_position:
            self.flown_path.append(self.drone_position)
        self.update()

    def update_field_of_view(self, field_of_view):
        for i in range(len(field_of_view)):
            field_of_view[i]["y"] *= -1
        self.field_of_view = field_of_view
        self.update()

    def update_animal_positions(self, position):
        if self.animal_position is None:
            self.animal_position = [0.0, 0.0]
        self.animal_position[0] = position["x"]
        self.animal_position[1] = position["y"]
        self.update()

    def to_QPointF(self, coordinate):
        return QPointF(coordinate["x"], coordinate["y"])

    def drawBackground(self, painter, rect):
        pen = QPen(QColor(50, 168, 82))
        pen.setWidth(1)
        painter.setPen(pen)

        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        right = int(rect.right())
        bottom = int(rect.bottom())

        # Draws vertical gridlines
        for x in range(left, right, self.grid_size * 4):
            painter.drawLine(x, int(rect.top()), x, bottom)
        # Draws horizontal gridlines
        for y in range(top, bottom, self.grid_size * 4):
            painter.drawLine(int(rect.left()), y, right, y)

        pen.setColor(QColor(50, 168, 82, 50))
        painter.setPen(pen)
        # Draws vertical gridlines
        for x in range(left, right, self.grid_size):
            painter.drawLine(x, int(rect.top()), x, bottom)
        # Draws horizontal gridlines
        for y in range(top, bottom, self.grid_size):
            painter.drawLine(int(rect.left()), y, right, y)

        pen.setColor(QColor(155, 155, 155))
        painter.setPen(pen)

        painter.setBrush(QColor(255, 255, 0, 200))
        polypoints = [self.to_QPointF(self.field_of_view[0]),
                      self.to_QPointF(self.field_of_view[1]),
                      self.to_QPointF(self.field_of_view[2]),
                      self.to_QPointF(self.field_of_view[3]),]

        for point in polypoints:
            point.setX(point.x() * self.grid_size)
            point.setY(point.y() * self.grid_size)

        painter.drawPolygon(QPolygonF(polypoints))

        # Draw drone position
        painter.setBrush(QColor(5, 80, 179))
        painter.drawEllipse(
            int(self.drone_position[0] - self.drone_size // 2),
            int(self.drone_position[1] - self.drone_size // 2),
            self.drone_size,
            self.drone_size
        )

        #self.graphicsView.centerOn(self.drone_position[0], self.drone_position[1])

        # Draw animal position
        if self.animal_position is None:
            return
        painter.setBrush(QColor(179, 16, 16))
        visual_animal_position = [int(self.animal_position[0] - self.animal_size / 2),
                                 int(self.animal_position[1] - self.animal_size / 2)]
        painter.drawEllipse(visual_animal_position[0], visual_animal_position[1], self.animal_size, self.animal_size)
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsEllipseItem, QGraphicsPolygonItem
from PyQt6.QtGui import QColor, QPolygonF, QBrush, QPen
from PyQt6.QtCore import QPointF, QLineF


class MapWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Scene
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.grid_size = 10
        self.add_grid(self.grid_size)

        # FOV
        self.field_of_view = [{'x': 0, 'y': 0},
                              {'x': 0, 'y': 0},
                              {'x': 0, 'y': 0},
                              {'x': 0, 'y': 0}]
        self.field_of_view_item = QGraphicsPolygonItem(to_QPolygonF(self.field_of_view))
        self.field_of_view_item.setBrush(QBrush(QColor(255, 255, 0, 120)))
        self.scene.addItem(self.field_of_view_item)

        # Animal
        self.animal_position = None
        self.animal_size = 10
        self.animal_item = QGraphicsEllipseItem(
            -self.animal_size / 2, -self.animal_size / 2,
            self.animal_size, self.animal_size
        )
        self.animal_item.setBrush(QBrush(QColor(179, 16, 16)))
        self.scene.addItem(self.animal_item)
        self.animal_item.hide()


        # Drone
        self.drone_position = {'x': 0, 'y': 0}
        self.drone_size = 10
        self.drone_item = QGraphicsEllipseItem(
            -self.drone_size/2, -self.drone_size/2,
            self.drone_size, self.drone_size
        )
        self.drone_item.setBrush(QBrush(QColor(5, 80, 179)))
        self.scene.addItem(self.drone_item)

        # Path
        self.flown_path = [{'x': 0, 'y': 0}]

        # Settings
        self.setRenderHint(self.renderHints().Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def update_drone_position(self, position):
        if self.drone_position != position:
            self.update_flown_path(position)
        self.drone_position = position
        self.drone_item.setPos(position["x"] * self.grid_size, position["y"] * self.grid_size)
        self.centerOn(self.drone_item)

        if len(self.flown_path) > 0 and self.flown_path[-1] != self.drone_position:
            self.flown_path.append(self.drone_position)

    def update_flown_path(self, position):
        pen_path = QPen(QColor(77, 228, 255))
        pen_path.setCosmetic(True)
        pen_path.setWidth(2)

        path = QLineF(self.flown_path[-1]["x"] * self.grid_size,
                      self.flown_path[-1]["y"] * self.grid_size,
                      position["x"] * self.grid_size,
                      position["y"] * self.grid_size)
        self.flown_path.append(position)
        self.scene.addLine(path, pen_path)


    def update_field_of_view(self, field_of_view):
        for i in range(len(field_of_view)):
            field_of_view[i]["y"] *= -1
        self.field_of_view = field_of_view

        for i in range(len(field_of_view)):
            field_of_view[i] = {"x": field_of_view[i]["x"] * self.grid_size, "y": field_of_view[i]["y"] * self.grid_size}
        self.field_of_view_item.setPolygon(to_QPolygonF(field_of_view))

    def update_animal_positions(self, position):
        if not position:
            self.animal_item.hide()
            return
        if not self.animal_position and position:
            self.animal_item.show()

        self.animal_position = position
        self.animal_item.setPos(position["x"] * self.grid_size, position["y"] * self.grid_size)

    def add_grid(self, spacing, size=10000):
        bounds = int(size / 2)
        self.scene.setSceneRect(-bounds, -bounds, size, size)

        pen_fine = QPen(QColor(50, 168, 82, 20))
        pen_fine.setCosmetic(True)  # stays 1px regardless of zoom
        pen_fine.setWidth(1)

        pen_thick = QPen(QColor(50, 168, 82))
        pen_thick.setCosmetic(True)
        pen_thick.setWidth(1)

        pen_axis = QPen(QColor(55, 212, 112))
        pen_axis.setCosmetic(True)
        pen_axis.setWidth(2)


        # Vertical lines - Small
        for x in range(-bounds, bounds, spacing):
            self.scene.addLine(x, -bounds, x, bounds, pen_fine)

        # Horizontal lines - Small
        for y in range(-bounds, bounds, spacing):
            self.scene.addLine(-bounds, y, bounds, y, pen_fine)

        # Vertical lines - Big
        for x in range(-bounds, bounds, spacing * 2):
            self.scene.addLine(x, -bounds, x, bounds, pen_thick)

        # Horizontal lines - Big
        for y in range(-bounds, bounds, spacing * 2):
            self.scene.addLine(-bounds, y, bounds, y, pen_thick)

        # XY-Axes at 0
        self.scene.addLine(-bounds, 0, bounds, 0, pen_axis)
        self.scene.addLine(0, -bounds, 0, bounds, pen_axis)

def to_QPolygonF(points):
    return QPolygonF([
        to_QPointF(points[0]),
        to_QPointF(points[1]),
        to_QPointF(points[2]),
        to_QPointF(points[3])
    ])

def to_QPointF(coordinate):
    return QPointF(coordinate["x"], coordinate["y"])
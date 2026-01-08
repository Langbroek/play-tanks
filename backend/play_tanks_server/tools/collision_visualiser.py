import json
import sys

from dataclasses import dataclass, asdict
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, 
    QGraphicsView, QGraphicsScene,
    QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QGroupBox,
    QFormLayout, QLineEdit,
    QPushButton, QGraphicsEllipseItem, QGraphicsLineItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QLineF, QObject, QTimer
from PyQt5.QtGui import QPen, QColor, QBrush, QCursor
from typing import Dict, Optional

from play_tanks_server.game.engine.math import Vec2, Transform
from play_tanks_server.game.engine.math.shapes import Segment
from play_tanks_server.game.engine.physics.engine2 import hitbox_intersection_2d
from play_tanks_server.game.objects import Tank
from play_tanks_server.game.models.stats import TankStats


@dataclass(frozen=True)
class TankData:
    name: str
    x_start: float
    y_start: float
    x_end: float
    y_end: float
    width: float
    height: float
    rotation: float = 0.0
    velocity: float = 0.0
    direction: Vec2 = Vec2(0, -1)


def load_data(title: str, **default_kwargs) -> TankData:
    """ Load kwargs from a config file or use defaults. """
    cwd = Path.cwd()
    config_path = cwd / "collision_visualiser_config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            if title in config:
                return TankData(**{'name': title, **config[title]})
        except Exception as e:
            print(f"Error loading config: {e}")
    return TankData(**{'name': title, **default_kwargs})


def save_data(data: dict):
    """ Save kwargs to a config file. """
    cwd = Path.cwd()
    config_path = cwd / "collision_visualiser_config.json"
    with open(config_path, 'w') as f:
        json.dump(data, f, indent=2)


class SlingshotScheduler(QObject):
    """
    A scheduler that delays the execution of a callback until a specified interval
    has passed without new scheduling requests. Each new request resets the timer.
    """
    finished = pyqtSignal()
    def __init__(self, delay_ms: int, **kwargs):
        super().__init__(**kwargs)
        self._delay_ms = delay_ms
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

    def schedule(self):
        """ Schedule the callback to be called after the interval. """
        if self._timer.isActive():
            self._timer.stop()
        self._timer.start(self._delay_ms)

    def force_schedule(self):
        """ Force the callback to be called after the interval, ignoring any existing timer. """
        if self._timer.isActive():
            self._timer.stop()
        self.finished.emit()

    def cancel(self):
        """ Cancel any scheduled callback. """
        if self._timer.isActive():
            self._timer.stop()

    def _on_timeout(self):
        """ Handle the timeout event. """
        self.finished.emit()

    def connect(self, callback):
        """ Connect a callback to the finished signal. """
        self.finished.connect(callback)

    def disconnect(self, callback):
        """ Disconnect a callback from the finished signal. """
        self.finished.disconnect(callback)


class TankStates(QObject):
    on_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.rot = Vec2(0, -1)
        self.tanks = {
            'tank_1': load_data('tank_1', x_start=500, y_start=800, x_end=500, y_end=100, width=20, height=35),
            'tank_2': load_data("tank_2", x_start=480, y_start=100, x_end=900, y_end=200, width=20, height=35)
        }
        # Update velocity and rotation.
        self._batch_update = True
        for tank in self.tanks.values():
            self.set_position(tank.name, Vec2(tank.x_start, tank.y_start), end=Vec2(tank.x_end, tank.y_end))

        self.save_timer = SlingshotScheduler(1000)
        self.save_timer.connect(self._save_states)

        self._batch_update = False
    
    def notify_change(self):
        """ Notify that the tank states have changed. """
        if not self._batch_update:
            self.on_changed.emit()
            self.save_timer.schedule()

    def set_tank(self, tank_data: TankData):
        """ Set kwargs for the specified tank. """
        self.tanks[tank_data.name] = tank_data
        self.notify_change()
    
    def get_data(self, tank_name: str) -> TankData:
        """ Get kwargs for the specified tank. """
        return self.tanks[tank_name]
        
    def create(self, tank_name: str) -> Tank:    
        data = self.get_data(tank_name)
        tank = Tank(
            Vec2(0,0),
            Transform(Vec2(data.x_start, data.y_start), data.direction),
            stats=TankStats(width=data.width, length=data.height, velocity=data.velocity)
        )
        return tank

    def set_size(self, tank_name: str, width: float, height: float):
        tank = self.get_data(tank_name)
        new_tank = TankData(**{**asdict(tank), 'width': width, 'height': height})
        self.set_tank(new_tank)

    def set_position(self, tank_name: str, start: Vec2, end: Optional[Vec2] = None, 
                     velocity: Optional[float] = None, rotation: Optional[float] = None):
        tank = self.get_data(tank_name)
        if end is None and velocity is not None and rotation is not None:
            # Compute based on velocity
            direction = self.rot.rotated_angle(rotation)
            end = start + direction.normalised() * velocity
        else:
            # Compute velocity based on end
            translation = end - start
            direction = translation.normalised()
            velocity = translation.magnitude()
            rotation = -(self.rot.rotated(direction)).to_degrees()
        new_tank = TankData(tank_name, float(start.x), float(start.y), float(end.x), float(end.y), 
                            tank.width, tank.height, float(rotation), float(velocity), direction)
        self.set_tank(new_tank)

    def _save_states(self):
        """ Force save the tank states immediately. """
        print('saving')
        data = {}
        for tank in self.tanks.values():
            data[tank.name] = asdict(tank)
            del data[tank.name]['direction']
        save_data(data)

    def __enter__(self):
        self._batch_update = True
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._batch_update = False
        self.notify_change()


class DraggablePoint(QGraphicsEllipseItem):
    def __init__(self, radius=4, on_move=None):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.setPos(0, 0)
        self.vector = Vec2(0, 0)

        self.setBrush(QBrush(Qt.red))
        self.setZValue(10)

        self.on_move = on_move
        self.blocked = False
        self.setAcceptHoverEvents(True)
        self.setFlags(
            QGraphicsEllipseItem.ItemIsSelectable |
            QGraphicsEllipseItem.ItemSendsScenePositionChanges |
            QGraphicsEllipseItem.ItemIsMovable
        )

    def hoverEnterEvent(self, event):
        """Change cursor to an open hand when the mouse enters the item's area."""
        self.setCursor(QCursor(Qt.ArrowCursor))
        event.accept()

    def hoverLeaveEvent(self, event):
        """Restore the default cursor when the mouse leaves, unless actively dragging."""
        self.setCursor(QCursor(Qt.ArrowCursor))
        event.accept()

    def get_pos(self) -> Vec2:
        """ Get the position of the point. """
        return self.vector

    def set_pos(self, pos: Vec2):
        """ Set the position of the point. """
        self.blocked = True
        self.setPos(pos.x, pos.y)
        self.vector = pos
        self.blocked = False

    def itemChange(self, change, value):
        if change == QGraphicsEllipseItem.ItemScenePositionHasChanged:
            if self.on_move and not self.blocked:
                self.vector = Vec2(value.x(), value.y())
                self.on_move(value)
        return super().itemChange(change, value)


class FloatSlider(QSlider):
    def __init__(self, min_f=0.0, max_f=1.0, step=0.001, parent=None):
        super().__init__(Qt.Horizontal, parent)

        self.min_f = min_f
        self.max_f = max_f
        self.step = step

        self.scale = int(round((max_f - min_f) / step))

        self.setMinimum(0)
        self.setMaximum(self.scale)

    def value_f(self) -> float:
        return self.min_f + self.value() * self.step

    def set_value_f(self, v: float):
        v = max(self.min_f, min(self.max_f, v))
        self.setValue(int(round((v - self.min_f) / self.step)))


class GraphView(QGraphicsView):
    def __init__(self):
        scene = QGraphicsScene(0, 0, 1024, 1024)
        super().__init__(scene)
        self.setMinimumSize(512, 512)
        self.resetTransform()
        self.scale(.5, .5)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self._lines = []
        self._line_index = 0
    
    def next_line(self) -> QGraphicsLineItem:
        """ Get the next line item for drawing. """
        if self._line_index >= len(self._lines):
            line = QGraphicsLineItem()
            self.scene().addItem(line)
            self._lines.append(line)
        line = self._lines[self._line_index]
        self._line_index += 1
        return line
    
    def reset_lines(self):
        """ Reset line index for new drawing. """
        self._line_index = 0    

    def wheelEvent(self, event):
        if event.angleDelta().y() == 0:
            return

        zoom_in = event.angleDelta().y() > 0
        factor = 1.15 if zoom_in else 1 / 1.15

        self.scale(factor, factor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.resetTransform()
            self.scale(.5, .5)
            event.accept()
        else:
            super().mousePressEvent(event)


class TankControls(QGroupBox):
    changed = pyqtSignal()
    def __init__(self, title):
        super().__init__(title)
        layout = QFormLayout()

        self._start_x = QLineEdit("0")
        self._start_x.textChanged.connect(self.emit_controls_changed)
        self._start_y = QLineEdit("0")
        self._start_y.textChanged.connect(self.emit_controls_changed)
        self._width = QLineEdit("0")
        self._width.textChanged.connect(self.emit_controls_changed)
        self._height = QLineEdit("0")
        self._height.textChanged.connect(self.emit_controls_changed)
        self._rotation = QLineEdit("0")
        self._rotation.textChanged.connect(self.emit_controls_changed)
        self._velocity = QLineEdit("0")
        self._velocity.textChanged.connect(self.emit_controls_changed)

        layout.addRow("start pos (x)", self._start_x)
        layout.addRow("start pos (y)", self._start_y)
        layout.addRow("width (float)", self._width)
        layout.addRow("height (float)", self._height)
        layout.addRow("rotation (float)", self._rotation)
        layout.addRow("velocity (float)", self._velocity)

        self.setLayout(layout)

        self._update_data = True
    
    def blockSignals(self, b):
        for widget in [self._start_x, self._start_y, self._width, self._height,
            self._rotation, self._velocity
        ]:
            widget.blockSignals(b)
        return super().blockSignals(b)

    def tank_start(self) -> Vec2:
        """ Get the tank start position. """
        return Vec2(float(self._start_x.text()), float(self._start_y.text()))
    
    def tank_size(self) -> tuple:
        """ Get the tank size (width, height). """
        return (float(self._width.text()), float(self._height.text()))
    
    def tank_rotation(self) -> float:
        """ Get the tank rotation. """
        return float(self._rotation.text())
    
    def tank_velocity(self) -> float:
        """ Get the tank velocity. """
        return float(self._velocity.text())
    
    def set_data(self, data: TankData):
        """ Set the control values from TankData. """
        if self._update_data is False:
            self._update_data = True
            return
        self.blockSignals(True)
        self._start_x.setText(str(data.x_start))
        self._start_y.setText(str(data.y_start))
        self._width.setText(str(data.width))
        self._height.setText(str(data.height))
        self._rotation.setText(str(data.rotation))
        self._velocity.setText(str(data.velocity))
        self.blockSignals(False)

    def emit_controls_changed(self):
        """ Check inputs and emit changed signal. """
        try:
            self.tank_size()
            self.tank_start()
            self.tank_velocity()
            self.tank_rotation()
            self._update_data = False
            self.changed.emit()
        except ValueError:
            pass


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tank Segment Visualizer")
        self.resize(1300, 700)
        self.tank_states = TankStates()
        self.tank_states.on_changed.connect(self.update_widgets)
        self._update_counter = 0

        # ── Graphs ─────────────────────────────
        self.real_graph = GraphView()
        self.relative_graph = GraphView()

        graphs_layout = QHBoxLayout()
        graphs_layout.addWidget(self.real_graph)
        graphs_layout.addWidget(self.relative_graph)

        # ── Time slider ────────────────────────
        self.time_slider = FloatSlider(0.0, 1.0, 0.001)
        self.time_slider.valueChanged.connect(self.update_graphs)
        time_layout = QVBoxLayout()

        # Collision
        collision_widget = QWidget()
        collision_layout = QHBoxLayout()
        self.time_label = QLabel("Collision Time ")
        collision_layout.addWidget(self.time_label)
        self.intersection_button = QPushButton("No Collision")
        self.intersection_button.clicked.connect(self.collide_tanks)
        self.recompute_button = QPushButton("Recompute Collision")
        self.recompute_button.clicked.connect(self.update_collisions)
        collision_layout.addWidget(self.intersection_button)
        collision_layout.addWidget(self.recompute_button)
        collision_widget.setLayout(collision_layout)

        time_layout.addWidget(collision_widget)
        time_layout.addWidget(self.time_slider)

        # ── Tank controls ──────────────────────
        self.tank_1 = TankControls("Tank 1 controls")
        self.tank_2 = TankControls("Tank 2 controls")
        self.tank_1.changed.connect(self.on_tank_change)
        self.tank_2.changed.connect(self.on_tank_change)

        tanks_layout = QHBoxLayout()
        tanks_layout.addWidget(self.tank_1)
        tanks_layout.addWidget(self.tank_2)

        # ── Root layout ────────────────────────
        root = QVBoxLayout()
        root.addLayout(graphs_layout)
        root.addLayout(time_layout)
        root.addLayout(tanks_layout)

        self.setLayout(root)

        self.tank1_pen = QPen(QColor("cyan"), 1)
        self.tank2_pen = QPen(QColor("magenta"), 1)
        self.tank1_path_pen = QPen(QColor("blue"), 1, Qt.DashLine)
        self.tank2_path_pen = QPen(QColor("red"), 1, Qt.DashLine)
        self.tank_hull_pen = QPen(QColor("black"), 1, Qt.DotLine)
        self.hit_pen = QPen(QColor("green"), 1)

        self._compute_intersection = False
        self._intersection = None

        # Setup dragging tank locations and velocity.
        self.tank_origins = {
            'tank_1': (
                DraggablePoint(on_move=self.on_tank_move),
                DraggablePoint(on_move=self.on_tank_move)
            ),
            'tank_2': (
                DraggablePoint(on_move=self.on_tank_move),
                DraggablePoint(on_move=self.on_tank_move)
            )
        }
        for (start, end) in self.tank_origins.values():
            self.real_graph.scene().addItem(start)
            self.real_graph.scene().addItem(end)

        self.tank_states.notify_change()

    def draw_tank(self, tank: Tank, graph: GraphView, pen: QPen, primary_tank: bool = False):
        distance = tank.get_distance(self.time_slider.value_f())
        for i, hull in enumerate(tank.hit_box.hulls()):
            moved_hull = hull.translated(distance)
            hull_pen = pen
            if primary_tank and i != 0:
                hull_pen = self.tank_hull_pen
            elif not primary_tank and self._intersection and self._intersection.hull_id == i:
                hull_pen = self.hit_pen

            line = graph.next_line()
            line.setPen(hull_pen)
            line.setLine(moved_hull.start.x, moved_hull.start.y, moved_hull.end.x, moved_hull.end.y)
        distance = tank.get_distance(1)
        aabb = tank.hit_box.aabb()
        aabb.expand(distance)

        for aabb_hull in aabb.hulls():
            line = graph.next_line()
            line.setPen(QPen(QColor("gray"), 1, Qt.DotLine))
            line.setLine(aabb_hull.start.x, aabb_hull.start.y, aabb_hull.end.x, aabb_hull.end.y)
    
    def draw_tank_path(self, tank: Tank, graph: GraphView, pen: QPen):
        start_pos = tank.position
        end_pos = start_pos + tank.get_distance(1)
        line = graph.next_line()
        line.setPen(pen)
        line.setLine(start_pos.x, start_pos.y, end_pos.x, end_pos.y)

    def draw_real_tank(self):
        self.real_graph.reset_lines()
        tank_1 = self.tank_states.create('tank_1')
        tank_2 = self.tank_states.create('tank_2')
        self.draw_tank(tank_1, self.real_graph, self.tank1_pen, True)
        self.draw_tank(tank_2, self.real_graph, self.tank2_pen)
        self.draw_tank_path(tank_1, self.real_graph, self.tank1_path_pen)
        self.draw_tank_path(tank_2, self.real_graph, self.tank2_path_pen)

    def draw_relative_tank(self):
        self.relative_graph.reset_lines()
        tank_1 = self.tank_states.create('tank_1')
        tank_2 = self.tank_states.create('tank_2')
        velocity = tank_1.get_distance() - tank_2.get_distance()
        tank_1.set_velocity(velocity.magnitude())
        tank_2.set_velocity(0.0)
        # Precompute hitbox
        tank_1.hit_box
        tank_1.transform.direction = velocity.normalised()

        if self._compute_intersection:
            self._intersection = hitbox_intersection_2d(tank_1.hit_box, tank_2.hit_box, velocity)
            if self._intersection is not None:
                self.intersection_button.setText(f"Collide Tanks at {self._intersection.time}")
            else:
                self.intersection_button.setText("No Collision")

        self.draw_tank(tank_1, self.relative_graph, self.tank1_pen, True)
        self.draw_tank(tank_2, self.relative_graph, self.tank2_pen)
        self.draw_tank_path(tank_1, self.relative_graph, self.tank1_path_pen)
    
    def update_widgets(self):
        """ Update widgets based on tank states. """
        for tank, controls in self.tank_controls.items():
            data = self.tank_states.get_data(tank)
            controls.set_data(data)
        for tank, (start, end) in self.tank_origins.items():
            data = self.tank_states.get_data(tank)
            start.set_pos(Vec2(data.x_start, data.y_start))
            end.set_pos(Vec2(data.x_end, data.y_end))

        self.update_collisions()

    def update_collisions(self):
        """ Update tanks based on control values. """
        self._compute_intersection = True
        self.update_graphs()
        self._compute_intersection = False

    def update_graphs(self):
        """ Update the graphs based on the current time slider value. """
        self._update_counter += 1
        self.draw_relative_tank()
        self.draw_real_tank()
        self.time_label.setText(f"Collision Time: {self.time_slider.value_f():.3f}")

    def collide_tanks(self):
        """ Move tanks to collision point. """
        if self._intersection is None:
            return
        
        t = self._intersection.time
        self.time_slider.set_value_f(t)
        self.update_graphs()

    def on_tank_change(self):
        """ Update tank states from controls. """
        with self.tank_states as state:
            for tank, controls in self.tank_controls.items():
                state.set_size(tank, *controls.tank_size())
                state.set_position(
                    tank, 
                    controls.tank_start(), 
                    velocity=controls.tank_velocity(), 
                    rotation=controls.tank_rotation()
                )

    def on_tank_move(self, *args):
        """ Handle tank point being moved. """
        with self.tank_states as state:
            for tank, (start, end) in self.tank_origins.items():
                state.set_position(tank, start.get_pos(), end=end.get_pos())

    @property
    def tank_controls(self) -> Dict[str, TankControls]:
        """ Get tank controls mapping. """
        return {
            'tank_1': self.tank_1,
            'tank_2': self.tank_2
        }

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    result = app.exec_()
    sys.exit(result)
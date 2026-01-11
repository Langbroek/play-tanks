import debugpy
import random
import sys

from PyQt5.QtCore import QRunnable, QObject, pyqtSignal, QThreadPool, Qt
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import QWidget, QApplication, QHBoxLayout, QVBoxLayout, QPushButton, QGroupBox

from play_tanks_server.game.engine.loop import GameLoop
from play_tanks_server.game.engine.math import Vec2
from play_tanks_server.game.models.encoding import EncodedGameWorld, EncodedEntity
from play_tanks_server.game.objects import Entity, Player
from play_tanks_server.game.state import GameMap, GameWorld
from play_tanks_server.game.state.actions import ACTION_TYPE as A, VectorAction, Action


def random_colour() -> QColor:
    """ Generates a random colour. """
    return QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


class GameLoopSignals(QObject):
    # Outgoing
    update = pyqtSignal(EncodedGameWorld)
    # Incoming
    request_move = pyqtSignal()
    request_abort = pyqtSignal()


class QGameLoop(QRunnable):

    def __init__(self, game: GameWorld):
        super().__init__()
        self.signals = GameLoopSignals()
        self.signals.request_abort.connect(self._thread_abort)
        self.signals.request_move.connect(self._move_player)
        self.game_loop = GameLoop(game=game, on_update=self._on_update)
        self.player = Player('Earl', Vec2(100, 0))
        self.game_loop.game.join(self.player)

    def start(self):
        if self.game_loop.running:
            return
        pool = QThreadPool.globalInstance()
        pool.start(self)

    def abort(self):
        self.signals.request_abort.emit()

    def _thread_abort(self):
        self.game_loop.stop()

    def _move_player(self):
        print('move player')

    def run(self):
        debugpy.debug_this_thread()
        self.game_loop.start()

    def _on_update(self, data: EncodedGameWorld):
        self.signals.update.emit(data)


class GameCanvas(QWidget):
    def __init__(self, game: GameWorld, player: Player):
        super().__init__()
        self.setFixedSize(*game.map.size)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.game = game
        self.player = player
        self._size = game.map.size
        self._data = None
        self._keys_down = set()
        self._tank_canvas_pos = None
        self._colours = {'tank': QColor(200, 50, 100)}
    
    def to_canvas_x(self, x: float) -> int:
        return int(x + (self._size[0] / 2))

    def to_canvas_y(self, y: float) -> int:
        return int(y + (self._size[1] / 2))

    def draw_rotated_rect(self, painter: QPainter, entity: EncodedEntity, idx: int):
        painter.save()

        #painter.translate(-cx, -cy)
        #painter.rotate(angle)
        painter.setPen(Qt.NoPen)

        key = 'tank' if entity.type == 'Tank' else idx
        colour = self._colours.setdefault(key, random_colour())

        painter.setBrush(colour)
        painter.translate(self.to_canvas_x(entity.x), self.to_canvas_y(-entity.y))

        if entity.rotation != 0:
            painter.rotate(entity.rotation)
            
        painter.drawRect(
            int(-entity.width / 2), 
            int(-entity.length / 2),
            int(entity.width),
            int(entity.length)
        )
        if entity.type != 'Tank':
            painter.restore()
            return
        # draw direction line
        painter.setPen(QPen(QColor(50, 200, 100), 2))
        painter.drawLine(0, 0, 0, -int(entity.length * 2))

        # draw cannon barrel
        barrel_rotation = entity.data.get('cannon_rotation', 0.0)
        painter_rotation = entity.rotation - barrel_rotation
        if painter_rotation != 0:
            painter.rotate(-painter_rotation)
        painter.setPen(QPen(QColor(100, 100, 250), 10))
        painter.drawLine(0, 0, 0, -int(entity.length * .75))

        painter.restore()
    
    def paintEvent(self, a0):
        if self._data is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for idx, entity in enumerate(self._data.entities):
            self.draw_rotated_rect(painter, entity, idx)
        painter.end()

    def draw_game(self, data: EncodedGameWorld):
        self._data = data
        for entity in data.entities:
            if entity.type == 'Tank':
                self._tank_canvas_pos = (
                    self.to_canvas_x(entity.x),
                    self.to_canvas_y(-entity.y)
                )
        self.update()

    def move_tank(self):
        direction = Vec2(0, 0)
        if Qt.Key_Left in self._keys_down:
            direction.x -= 1
        if Qt.Key_Right in self._keys_down:
            direction.x += 1
        if Qt.Key_Up in self._keys_down:
            direction.y += 1
        if Qt.Key_Down in self._keys_down:
            direction.y -= 1  # Down should be positive y
        # Send action to game loop
        self.game.handle_player_action(self.player, VectorAction(direction, A.MOVE, self.player))

    def rotate_barrel(self):
        if self._tank_canvas_pos is None or self._mouse_canvas_pos is None:
            return
        tank_x, tank_y = self._tank_canvas_pos
        mouse_x, mouse_y = self._mouse_canvas_pos
        direction = Vec2(mouse_x - tank_x, tank_y - mouse_y)
        # Send aim action to game loop
        self.game.handle_player_action(self.player, VectorAction(direction, A.AIM, self.player))

    def shoot(self):
        self.game.handle_player_action(self.player, Action(A.SHOOT, self.player))

    def keyPressEvent(self, event):
        key = event.key()
        if key not in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            return
        self._keys_down.add(key)
        self.move_tank()
        self.rotate_barrel()
    
    def keyReleaseEvent(self, event):
        key = event.key()
        if key in self._keys_down:
            self._keys_down.remove(key)
        self.move_tank()
        self.rotate_barrel()

    def mouseMoveEvent(self, event):
        if self._tank_canvas_pos is None:
            return super().mouseMoveEvent(event)
        x, y = event.x(), event.y()
        self._mouse_canvas_pos = (x, y)
        self.rotate_barrel()
        return super().mouseMoveEvent(event)
    
    def mousePressEvent(self, a0):
        self.shoot()
        return super().mousePressEvent(a0)


class GameVisualiser(QWidget):
    
    def __init__(self, game_map: GameMap):
        super().__init__()
        self.loop = QGameLoop(GameWorld(map=game_map))
        self.loop.signals.update.connect(self._on_game_update)

        layout = QHBoxLayout()
        self.canvas = GameCanvas(self.loop.game_loop.game, self.loop.player)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        panel_group = QGroupBox("Controls")
        panel = QVBoxLayout()
        start_button = QPushButton("Start")
        start_button.clicked.connect(self.loop.start)
        panel.addWidget(start_button)
        abort_button = QPushButton("Abort")
        abort_button.clicked.connect(self.loop.abort)
        panel.addWidget(abort_button)
        panel_group.setLayout(panel)

        request_update = QPushButton("Request Update")
        request_update.clicked.connect(self.loop.game_loop.request_update)
        panel.addWidget(request_update)

        layout.addWidget(panel_group)

    
    def _on_game_update(self, data: EncodedGameWorld):
        # Handle the updated game world data (e.g., render it)
        self.canvas.draw_game(data)
        

if __name__ == "__main__":
    import numpy as np
    app = QApplication(sys.argv)

    import logging
    logging.basicConfig(level=logging.INFO)

    # Create a sample game map
    game_map =  GameMap(np.array([
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1],
        [1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, .2, .2, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, .2, .2, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, .2, 0, 0, 0, 1],
        [1, 0, 0, 1, 1, .2, .2, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    ]), scale=70)

    # Create the game visualiser
    visualiser = GameVisualiser(game_map)
    visualiser.show()

    sys.exit(app.exec_())

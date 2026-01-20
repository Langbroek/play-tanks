import time
import logging
from typing import Optional

from play_tanks_server.game.objects import GameObject
from play_tanks_server.game.state import GameWorld


logger = logging.getLogger(__name__)


class GameLoop(GameObject):

    def __init__(self, game: GameWorld, tick_rate: float = 60.0, on_update=None):
        super().__init__()
        self.game = game
        self.tick_rate = tick_rate
        self.delta_time = 1.0 / tick_rate
        self.last_time: Optional[float] = None
        self.running = False
        self._on_update = on_update
    
    def request_update(self):
        if self._on_update is not None:
            self._on_update(self.game.encode())

    def start(self):
        import debugpy
        debugpy.debug_this_thread()
        self.running = True
        while self.running:
            start = time.perf_counter()
            if self.last_time is None:
                delta = self.delta_time
            else:
                delta = min(start - self.last_time, self.delta_time)
            self.last_time = start
            
            self.game.update(delta)
            if self._on_update is not None:
                self._on_update(self.game.encode())

            elapsed = time.perf_counter() - start
            if elapsed < self.delta_time:
                time.sleep(self.delta_time - elapsed)
            else:
                logger.warning(f"Game {str(self)} is running behind schedule by "
                               f"{elapsed - self.delta_time:.4f} seconds")

    def stop(self):
        self.running = False
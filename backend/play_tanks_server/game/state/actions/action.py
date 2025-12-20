import time

from play_tanks_server.game.objects import GameObject
from play_tanks_server.game.state.actions import ACTION_TYPE


class Action:
    
    def __init__(self, action: ACTION_TYPE, owner: GameObject):
        self.type = action
        self.owner = owner
        self.created = time.time()


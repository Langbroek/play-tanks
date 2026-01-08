from play_tanks_server.game.engine.math import Vec2
from play_tanks_server.game.objects import GameObject
from play_tanks_server.game.state.actions import ACTION_TYPE, Action


class VectorAction(Action):
    
    def __init__(self, vector: Vec2, action: ACTION_TYPE, owner: GameObject):
        super().__init__(action, owner)
        self.vector = vector
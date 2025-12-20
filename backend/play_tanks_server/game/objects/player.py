from play_tanks_server.game.objects import GameObject


class Player(GameObject):

    def __init__(self, username: str):
        super().__init__()
        self.username = username
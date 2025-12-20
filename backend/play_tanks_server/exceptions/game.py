from play_tanks_server.exceptions.base import BaseException


class GameException(BaseException):
    """ 
    Base exception for game-related errors.
    """
    def __init__(self, message: str = "An error occurred in the game.", prefix_class: bool = True):
        if prefix_class:
            exception_name = self.__class__.__name__
            if exception_name.lower().endswith("exception"):
                exception_name = exception_name[:-9]
            message = f"{exception_name}: {message}"
        super().__init__(message)


class EntityNotFoundException(GameException):
    pass


class PlayerNotFoundException(EntityNotFoundException):
    pass


class InvalidGameStateException(GameException):
    pass


class GameAlreadyStartedException(GameException):
    pass


class GameNotActiveException(GameException):
    pass


class PlayerAlreadyInGameException(GameException):
    pass


class MaxPlayersReachedException(GameException):
    pass


class InvalidPlayerActionException(GameException):
    pass

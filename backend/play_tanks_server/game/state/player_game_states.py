from typing import Dict, Optional, List, Tuple, Generator, Union, Literal, overload

from play_tanks_server.exceptions import (MaxPlayersReachedException, PlayerAlreadyInGameException, 
                                          PlayerNotFoundException)

from play_tanks_server.game.objects import Player, Tank, Projectile
from play_tanks_server.game.state.actions import ACTION_TYPE as A, Action, VectorAction


class PlayerGameState:

    def __init__(self, player: Player):
        self.player = player
        self.tank = Tank()
        self.actions: Dict[A, Optional[Action]] = {
            A.MOVE: None,
            A.ROTATE: None,
            A.SHOOT: None,
            A.BOMB: None
        }
        self.removal_requested = False
        self.is_alive: bool = True

    @overload
    def pop_action(self, action_type: Literal[A.MOVE, A.ROTATE]) -> Optional[VectorAction]: ...
    @overload
    def pop_action(self, action_type: Literal[A.SHOOT, A.BOMB]) -> Optional[Action]: ...

    def pop_action(self, action_type: A) -> Optional[Action]:
        """ Retrieve and clear the current action of a specific type. """
        action = self.actions.get(action_type)
        self.actions[action_type] = None
        return action


class PlayerGameStates:

    def __init__(self, max_players: int):
        self.max_players = max_players
        self.players: Dict[Player, PlayerGameState] = {}

    def add(self, player: Player):
        """ Initialize a player's game state. """
        if len(self.players) >= self.max_players:
            raise MaxPlayersReachedException(f"Cannot add player {player}: max players reached.")
        if player in self.players:
            raise PlayerAlreadyInGameException(f"Player {player} is already in the game.")
        self.players[player] = PlayerGameState(player)

    def remove(self, player: Player):
        """ Remove a player's game state. """
        if player not in self.players:
            raise PlayerNotFoundException(f"Player {player} not found in game states.")
        state = self.players[player]
        state.removal_requested = True

    def players_remove_requested(self) -> Generator[Tuple[Player, PlayerGameState], None, None]:
        """ Iterate over players who have requested removal. """
        for player, state in self.players.items():
            if state.removal_requested:
                yield player, state

    def clear_removals(self):
        """ Clear all players who have requested removal. """
        self.players = {
            player: state for player, state in self.players.items() if not state.removal_requested
        }

    def __len__(self):
        return len(self.players)
    
    def __iter__(self):
        return iter(self.players.values())
    
    def alive(self) -> Generator[PlayerGameState, None, None]:
        """ Iterate over players who are alive. """
        for state in self.players.values():
            if state.is_alive:
                yield state

    def projectiles(self) -> Generator[Projectile, None, None]:
        """ Iterate over all projectiles from all players. """
        for state in self.players.values():
            for projectile in state.tank.projectiles:
                yield projectile

    def entities(self) -> Generator[Union[Tank, Projectile], None, None]:
        """ Iterate over all entities (tanks and projectiles) from all players. """
        for state in self.players.values():
            yield state.tank
            for projectile in state.tank.projectiles:
                yield projectile

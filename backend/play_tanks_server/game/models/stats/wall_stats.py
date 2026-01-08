from dataclasses import dataclass

from play_tanks_server.game.models.stats import StaticStats


@dataclass(frozen=True)
class WallStats(StaticStats):
    """
      Wall stats.
    """
    durability: float = 1.0  # Random flag for now. no use

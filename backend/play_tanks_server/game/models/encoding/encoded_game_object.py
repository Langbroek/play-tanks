from dataclasses import dataclass


@dataclass(frozen=True)
class EncodedGameObject:
    """ Encoded representation of the game world. """
    uid: str
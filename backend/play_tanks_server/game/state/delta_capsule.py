from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar('T')


@dataclass
class DeltaCapsule(Generic[T]):
    """ A capsule representing a change in state over time. """
    data: T
    timestamp: float = 0.0
    iteration: int = 0
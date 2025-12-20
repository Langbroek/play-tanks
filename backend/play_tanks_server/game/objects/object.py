import uuid

from play_tanks_server.core.log import Loggable


class GameObject(Loggable):

    def __init__(self):
        super().__init__()
        self.uid = str(uuid.uuid4())

    def __eq__(self, value):
        if not isinstance(value, GameObject):
            return False
        return self.uid == value.uid
    
    def __ne__(self, value):
        return not self.__eq__(value)
    
    def __hash__(self):
        return hash(self.uid)

    def __str__(self):
        return f"{self.__class__.__name__}<{self.uid}>"
    
    def _format(self, string: str, **kwargs) -> str:
        """ Format string and include self if needed. """
        if "{self}" in string:
            kwargs["self"] = self
        return string.format(**kwargs)

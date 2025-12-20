

class BaseException(Exception):
    """Base exception for the play tanks server."""
    pass


def with_exception_context(func):
    """ Decorator to add object context to exceptions raised in the method. """
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            e.args = (f"[{self}]", *e.args)
            raise e
    return wrapper
import logging
import time

from typing import Dict, Optional, Generator, Tuple


def kwargs_to_string(**kwargs) -> str:
    """ Format keyword arguments into a string for logging. """
    return ", ".join(f"{key}={value}" for key, value in kwargs.items())


def get_function_stats(func, *args, **kwargs) -> str:
    """ Get the function name with parameters for logging. """
    return f"{func.__name__}({', '.join(map(str, args))}, {kwargs_to_string(**kwargs)})"


class LogItem:
    
    def __init__(self, ctx_key: str = "", message: str = ""):
        self.ctx_key = ctx_key
        self.message = message
        self._counter = 0
        self._total_time = 0.0
        self._start_time = 0.0
    
    def set_message(self, message: str):
        """ Update the log message. """
        self.message = message

    def log_message(self, message: str):
        """ Set log message and increment counter. """
        self.message = message
        self._counter += 1

    def format_log_message(self, reset: bool = True) -> str:
        """ Formats the log message with timing info and resets counters if needed. """
        if self._total_time > 0:
            avg_time = self._total_time / self._counter
            formatted = (
                f"[{self.ctx_key}] {self.message}, Total Time: {self._total_time:.6f}s, "
                f"Avg Time: {avg_time:.6f}s"
            )
        else:
            formatted = f"[{self.ctx_key}] {self.message}"
        if reset:
            self._counter = 0
            self._total_time = 0.0
        return formatted
    
    def increment(self):
        """ Increment the counter by one. """
        self._counter += 1

    def can_log(self, every_n: int) -> bool:
        return every_n > 0 and self._counter % every_n == 0

    def __enter__(self):
        self._start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._total_time += (time.perf_counter() - self._start_time)
        self._counter += 1


class ContextLogger(logging.Logger):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_context: Dict[str, LogItem] = {}
    
    def context(self, key: str, message: Optional[str] = None) -> LogItem:
        """ Get context key """
        item = self._log_context.setdefault(key, LogItem(ctx_key=key))
        if message is not None:
            item.set_message(message)
        return item
    
    def contexts(self, key: str) -> Generator[LogItem, None, None]:
        """ Generator for all context items that start with the given key. """
        if key == "":
            return None
        for item in self._log_context.values():
            if item.ctx_key.startswith(key):
                yield item

    def log_context(self, key: str = ""):
        """ Log all context items that start with the given key. """
        item = self._log_context.get(key)
        if item is not None:
          self.info(item.format_log_message())
        for item in self.contexts(key):
            if item.ctx_key == key:
                continue  # Ignore parent.
            self.info(item.format_log_message())


logger = ContextLogger(__name__)


class Loggable:
    
    def __init__(self):
        self._logger = None

    @property
    def logger(self) -> ContextLogger:
        if self._logger is None:
            return logger # Fallback to module logger
        return self._logger
    
    def init_logger(self):
        """ Initialize the logger for this object. """
        if self._logger is not None:
            return
        self._logger = ContextLogger(str(self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}"


def get_logger_and_args(*args) -> Tuple[ContextLogger, tuple]:
    """ Get logger from first Loggable argument or fallback to module logger. """
    if len(args) > 0 and isinstance(args[0], Loggable):
        return args[0].logger, args[1:]
    return logger, args


def with_function_logger(func=None, 
                         context: str = "",
                         log_every_n: int = -1,
                         timed: bool = True):
    """ 
      Decorator to add context logging to methods.   
      if message is None function name will be used.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal context
            logger_, f_args = get_logger_and_args(args)
            if context == "":
                context = func.__name__
            message = get_function_stats(func, *f_args, **kwargs)
            log_item = logger_.context(context, message)
            if timed:
                with log_item:
                    result = func(*args, **kwargs)
                log_item.set_message(message)
            else:
                result = func(*args, **kwargs)
                log_item.log_message(message)
            if log_item.can_log(log_every_n):
                logger.log_context(context)
            if log_every_n > 0 and log_item._counter % log_every_n == 0:
                logger_.log_context(context)
            return result
        return wrapper
    if func is None:
        return decorator
    else:
        return decorator(func)
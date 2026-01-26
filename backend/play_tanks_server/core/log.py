import logging
import time

from typing import Dict, Optional, Generator, Tuple
from typing_extensions import Self


def kwargs_to_string(**kwargs) -> str:
    """ Format keyword arguments into a string for logging. """
    return ", ".join(f"{key}={value}" for key, value in kwargs.items())


def func_to_string(func, *args, log_params: bool = False, **kwargs) -> str:
    """ Get the function name with parameters for logging. """
    if not log_params:
        return func.__name__ + "()"
    return f"{func.__name__}({', '.join(map(str, args))}, {kwargs_to_string(**kwargs)})"


class LogTimer:

    def __init__(self, time_limit: float = 1e-6):
        self._start_time: Optional[float] = None
        self._total_time: float = 0.0
        self._max_time: float = 0.0
        self._min_time: float = float('inf')
        self._timer_count: int = 0
        self._enabled = False
        self._time_limit = time_limit

    def start(self):
        self._start_time = time.perf_counter()
        self._enabled = True
    
    def stop(self):
        if not self._enabled or self._start_time is None:
            return
        elapsed = time.perf_counter() - self._start_time
        self._total_time += elapsed
        self._max_time = max(self._max_time, elapsed)
        self._min_time = min(self._min_time, elapsed)
        self._timer_count += 1

    def reset(self):    
        self._start_time = None
        self._total_time = 0.0
        self._max_time = 0.0
        self._min_time = float('inf')
        self._timer_count = 0

    def __str__(self) -> str:
        if self._timer_count <= 0 or self._total_time < self._time_limit:
            return ""
        fps = self._timer_count / self._total_time if self._total_time > 0 else 0.0
        fps_str = f"({fps:.2f} fps) " if fps > 0 else ""
        avg_time = self._total_time / self._timer_count if self._timer_count > 0 else 0.0
        return f" - {fps_str} (total, avg, max, min) time: | {self._total_time:.6f}s | "\
               f"{avg_time:.6f}s | {self._max_time:.6f}s | {self._min_time:.6f}s |"        


class LogContext:
    def __init__(self, name: str):
        self.name = name
        self._contexts: Dict[str, LogContext] = {}
        self._title = name
        self._log_count = 0
        self._timer = LogTimer()
    
    def get(self, name: str) -> Self:
        if name == "":
            return self  # Main context
        if "." in name:
            parts = name.split(".")
            ctx = self
            for part in parts:
                ctx = ctx.get(part)
            return ctx

        return self._contexts.setdefault(name, LogContext(name))
    
    def set_title(self, title: str):
        """ Set title for this context. """
        self._title = title

    def can_log(self, count: int) -> bool:    
        return self._log_count >= count

    def increment(self):
        """ Increment log counter for this context. """
        self._log_count += 1

    def reset(self):
        """ Reset log counter for this context and all sub-contexts. """
        self._log_count = 0
        self._timer.reset()
        for ctx in self._contexts.values():
            ctx.reset()

    def format_log_message(self, index: int = 0) -> str:
        """ Format log message for this context and all sub-contexts. """
        indent = "  " * index
        message = f"{indent} Func {self._title}{str(self._timer)}"
        if len(self._contexts) == 0:
            return message
        message += ":\n"
        for i, ctx in enumerate(self._contexts.values()):
            message += ctx.format_log_message(index + 1)
            if i < len(self._contexts) - 1:
                message += "\n"
        return message
    
    def __enter__(self):
        self._timer.start()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._timer.stop()


class ContextLogger:
    
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        self._log_context = LogContext(name)
        self._active_contexts = []
    
    def activate_context(self, context: str, sub_context: str) -> LogContext:
        """ Get context key """
        parent = self._log_context.get(context)
        child = parent.get(sub_context)
        active_context = f"{context}.{sub_context}" if context != "" else sub_context
        self._active_contexts.append(active_context)
        return child
    
    def deactivate_context(self, context: str, sub_context: str):
        """ Deactivate context key """
        active_context = f"{context}.{sub_context}" if context != "" else sub_context
        if active_context in self._active_contexts:
            self._active_contexts.remove(active_context)

    def info(self, message: str):
        """ Log an info message. """
        self._logger.info(message)

    def warning(self, message: str):
        """ Log a warning message. """
        self._logger.warning(message)
    
    def error(self, message: str):
        """ Log an error message. """
        self._logger.error(message)

    def exception(self, message: str):
        """ Log an exception message. """
        self._logger.exception(message)

    def log_context(self, context: str = "", every_n: int = 1):
        """ Log all context items that start with the given key. """
        ctx = self._log_context.get(context)
        if ctx.can_log(every_n):
            self.info(
                ctx.format_log_message()
            )
            ctx.reset()
        else:
            ctx.increment()

    def time(self, context: str, parent_context: Optional[str] = None) -> LogTimer:
        """ 
        Start a timer for the given context. Providing None for parent will find the active 
        parent from the context tree. If empty string is provided it will use the root context. 
        Otherwise it will use the provided parent context. 
        """
        if parent_context == "" or len(self._active_contexts) == 0:
            parent = self._log_context
        elif parent_context is not None:
            parent = self._log_context.get(parent_context)
        else:
            parent = self._log_context.get(self._active_contexts[-1])
        ctx = parent.get(context)
        ctx._timer.start()
        return ctx._timer


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
                         log_params: bool = True,
                         timed: bool = True,
                         disabled: bool = False):
    """ 
      Decorator to add context logging to methods.   
      if message is None function name will be used.
    """
    def decorator(func):            
        if disabled:
            return func
        def wrapper(*args, **kwargs):
            nonlocal context
            logger_, f_args = get_logger_and_args(*args)
            sub_context = func.__name__
            func_title = func_to_string(func, *f_args, log_params=log_params, **kwargs)
            log_ctx = logger_.activate_context(context, sub_context)
            log_ctx.set_title(func_title)
            if timed:
                with log_ctx:
                    result = func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            if context != "" and log_every_n > 0:
                # is main context.
                logger_.log_context(context, log_every_n)
            elif context == "":
                logger_.log_context(sub_context, log_every_n)
            logger_.deactivate_context(context, sub_context)
            return result
        return wrapper
    if func is None:
        return decorator
    else:
        return decorator(func)
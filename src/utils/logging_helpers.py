import logging
from contextlib import contextmanager

def setup_logging(
    log_file="app.log", 
    log_level=logging.INFO, 
    log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
):
    """
    Sets up the global logging configuration.
    
    Args:
        log_file (str): Path to the log file.
        log_level (int): Logging level (e.g., logging.INFO).
        log_format (str): Format for log messages.
    """
    logging.basicConfig(
        filename=log_file,
        level=log_level,
        format=log_format,
        filemode="a",  # Append to the log file
    )

    # Add console handler for real-time logging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(console_handler)

    logging.info("Logging initialized.")


def get_logger(name, log_file=None, log_level=logging.INFO):
    """
    Returns a custom logger for a specific module or task.

    Args:
        name (str): Name of the logger (usually the module name).
        log_file (str): Path to a specific log file for this logger.
        log_level (int): Logging level (e.g., logging.INFO).

    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Add file handler if a specific log file is provided
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        logger.addHandler(file_handler)

    return logger


@contextmanager
def log_context(name):
    """
    Logs the start and end of a context for better debugging and tracking.

    Args:
        name (str): Name of the context or operation.
    """
    logging.info(f"Starting: {name}")
    try:
        yield
    finally:
        logging.info(f"Finished: {name}")


def log_exceptions(func):
    """
    Decorator to log exceptions raised by a function.

    Args:
        func (Callable): The function to wrap.

    Returns:
        Callable: The wrapped function with exception logging.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Exception in {func.__name__}: {e}", exc_info=True)
            raise
    return wrapper


def set_log_level(level):
    """
    Dynamically changes the log level for the root logger.

    Args:
        level (int or str): New log level (e.g., logging.DEBUG or "DEBUG").
    """
    if isinstance(level, str):
        # Convert level name to numeric value if provided as a string
        level = logging.getLevelName(level.upper())
        if not isinstance(level, int):
            raise ValueError(f"Invalid log level string: {level}")
    elif not isinstance(level, int):
        raise ValueError(f"Invalid log level type: {type(level)}. Expected int or str.")

    # Set the new log level
    logging.getLogger().setLevel(level)
    logging.info(f"Log level changed to {logging.getLevelName(level)}")
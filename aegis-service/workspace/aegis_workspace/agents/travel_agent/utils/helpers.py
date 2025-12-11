import time
import logging

logger = logging.getLogger(__name__)

def retry(max_retries=3, delay=2):
    """
    A decorator that retries a function a specified number of times with a delay between retries.

    Args:
        max_retries (int): The maximum number of times to retry the function.
        delay (int): The delay in seconds between retries.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Attempt {retries + 1} failed: {e}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    retries += 1
            logger.error(f"Function {func.__name__} failed after {max_retries} retries.")
            raise  # Re-raise the last exception
        return wrapper
    return decorator
import time
import functools
from .utils import load_cache, save_cache

def cache_result(expiry_seconds: int):
    """
    A decorator to cache the results of a function for a specified duration.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # The first argument is expected to be 'self' of a class instance.
            if not args or not hasattr(args[0], 'project_root'):
                # Cannot determine a unique cache key, so run the function without caching.
                return func(*args, **kwargs)

            self = args[0]
            
            # Generate a cache key based on the function's name and project.
            # This is a simplified key; for more complex cases, we might need to inspect args/kwargs.
            cache_key = f"{func.__name__}:{self.project_root.name}"

            cache = load_cache()
            cached_data = cache.get(cache_key)

            if cached_data and (time.time() - cached_data.get('timestamp', 0) < expiry_seconds):
                return cached_data['data']

            # Execute the function to get fresh data.
            result = func(*args, **kwargs)

            # Save the new data to the cache.
            cache[cache_key] = {'data': result, 'timestamp': time.time()}
            save_cache(cache)

            return result
        return wrapper
    return decorator
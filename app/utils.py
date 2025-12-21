""" Generic Utilities """

import threading
import functools

# Function synchronization with an RLock, from Gemini
def synchronized(method):
    """
    A decorator to synchronize access to a method on a per-instance basis.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        # The lock is stored in the instance's __dict__ to avoid 
        # issues if the method is called during initialization.
        lock_name = f'_{method.__name__}_lock'
        if not hasattr(self, lock_name):
            # Use RLock to prevent deadlocks if a synchronized method 
            # calls another synchronized method within the same instance.
            setattr(self, lock_name, threading.RLock())
        
        lock = getattr(self, lock_name)
        
        with lock:
            return method(self, *args, **kwargs)
            
    return wrapper


# Classproperty
class classproperty(property):
    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)

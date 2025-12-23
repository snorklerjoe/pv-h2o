""" Generic Utilities """

import threading
import functools
import ctypes
from loguru import logger

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

def run_with_timeout_and_kill(func, args=(), kwargs=None, timeout=10):
    """
    Runs a function in a separate thread. If it exceeds the timeout,
    it attempts to raise an exception in the thread to kill it.
    """
    if kwargs is None:
        kwargs = {}

    class ThreadKilledException(Exception):
        pass

    def target():
        try:
            func(*args, **kwargs)
        except ThreadKilledException:
            logger.warning(f"Thread running {func.__name__} was killed due to timeout.")
        except Exception as e:
            logger.exception(f"Error in {func.__name__}: {e}")

    t = threading.Thread(target=target, name=f"TimeoutWrapper-{func.__name__}", daemon=True)
    t.start()
    t.join(timeout)

    if t.is_alive():
        logger.error(f"Function {func.__name__} timed out after {timeout}s. Attempting to kill...")
        
        # Attempt to raise exception in thread
        tid = t.ident
        if tid:
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(ThreadKilledException))
            if res == 0:
                logger.error("Invalid thread ID when trying to kill thread.")
            elif res > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), 0)
                logger.error("PyThreadState_SetAsyncExc failed.")
        else:
            logger.error("Thread ID is None, cannot kill.")

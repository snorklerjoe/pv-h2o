import pytest
import threading
import time
from app.utils import synchronized, classproperty

class TestUtils:
    def test_synchronized(self):
        class Counter:
            def __init__(self):
                self.count = 0
            
            @synchronized
            def increment(self):
                current = self.count
                time.sleep(0.01) # Force context switch potential
                self.count = current + 1

        counter = Counter()
        threads = []
        for _ in range(50):
            t = threading.Thread(target=counter.increment)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
            
        assert counter.count == 50

    def test_classproperty(self):
        class A:
            classval = 2.0
            @classproperty
            def myprop(cls):
                return cls.classval * 2.0
        class B(A):
            classval = 3.0
        
        assert A.myprop == 4.0
        assert B.myprop == 6.0  # `cls` should follow the subclass

import pytest
import threading
import time
from app.utils import synchronized

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

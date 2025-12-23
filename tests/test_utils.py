import pytest
import threading
import time
from app.utils import synchronized, classproperty, run_with_timeout_and_kill

class TestUtils:
    def test_run_with_timeout_and_kill_success(self):
        result = {"completed": False}
        def task():
            time.sleep(0.1)
            result["completed"] = True
        
        run_with_timeout_and_kill(task, timeout=1.0)
        assert result["completed"] is True

    def test_run_with_timeout_and_kill_timeout(self):
        result = {"completed": False}
        def task():
            try:
                time.sleep(2.0)
                result["completed"] = True
            except Exception:
                # If the thread is killed, we might catch the exception here if we were catching BaseException
                # But we are just checking if it finished
                pass
        
        start_time = time.time()
        run_with_timeout_and_kill(task, timeout=0.5)
        duration = time.time() - start_time
        
        # It should return roughly around the timeout
        assert duration < 1.5 
        # It should NOT have completed
        assert result["completed"] is False

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

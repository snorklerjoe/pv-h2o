import random
from drivers.base_driver import BaseSensorDriver, BaseOutputDriver, BaseLCDDriver

@BaseSensorDriver.register_driver("dummy")
class DummySensorDriver(BaseSensorDriver):
    def hardware_init(self):
        pass

    def read(self):
        # Return a value based on params, or a random value if not specified
        base_value = float(self.params.get('value', 0.0))
        noise = float(self.params.get('noise', 0.0))
        return base_value + random.uniform(-noise, noise)

@BaseOutputDriver.register_driver("dummy")
class DummyOutputDriver(BaseOutputDriver):
    def __init__(self, params=None):
        super().__init__(params)
        self._state = False

    def hardware_init(self):
        pass

    def set_state(self, state):
        self._state = state
        print(f"DummyOutputDriver: Set state to {state}")

    def get_state(self):
        return self._state
    
@BaseLCDDriver.register_driver("dummy")
class DummyLCDDriver(BaseLCDDriver):
    def hardware_init(self):
        pass

    def write_line(self, line_num, text):
        print(f"DummyLCDDriver: Line {line_num}: {text}")

    def clear(self):
        print("DummyLCDDriver: Cleared")

    def set_backlight(self, state):
        print(f"DummyLCDDriver: Backlight {'ON' if state else 'OFF'}")

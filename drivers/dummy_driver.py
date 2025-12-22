import random
from drivers.base_driver import BaseSensorDriver, BaseOutputDriver, BaseLCDDriver, BaseGFCIDriver

@BaseSensorDriver.register_driver("dummy")
class DummySensorDriver(BaseSensorDriver):
    def hardware_init(self):
        pass
    def hardware_deinit(self):
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
    def hardware_deinit(self):
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
    def hardware_deinit(self):
        pass

    def write_line(self, line_num, text):
        print(f"DummyLCDDriver: Line {line_num}: {text}")

    def clear(self):
        print("DummyLCDDriver: Cleared")

    def set_backlight(self, state):
        print(f"DummyLCDDriver: Backlight {'ON' if state else 'OFF'}")

@BaseGFCIDriver.register_driver("dummy")
class DummyGFCIDriver(BaseGFCIDriver):
    _instances = {}

    def hardware_init(self):
        pass
    def hardware_deinit(self):
        pass

    def set_tolerance(self, value: float):
        """ Sets a new value for fault detection tolerance """
        print(f"DUMMY_DRIVER: Setting GFCI tolerance to {value}")

    def set_threshold(self, value: float):
        """ Sets a new value for fault detection threshold """
        print(f"DUMMY_DRIVER: Setting GFCI threshold to {value}")

    def set_tripped(self, circuit: int):
        """ Forces the circuit to trip (circuit 1 or circuit 2) """
        print(f"DUMMY_DRIVER: Tripping circuit {circuit}")
        if not hasattr(self, '_tripped'):
            self._tripped = {}
        self._tripped[circuit] = True

    def reset_tripped(self, circuit: int):
        """ Forces the circuit to cease to be tripped (circuit 1 or circuit 2) """
        print(f"DUMMY_DRIVER: Un-Tripping circuit {circuit}")
        if not hasattr(self, '_tripped'):
            self._tripped = {}
        self._tripped[circuit] = False

    def is_tripped(self, circuit: int) -> bool:
        if not hasattr(self, '_tripped'):
            return False
        return self._tripped.get(circuit, False)

    def ping(self) -> bool:
        """ Checks connection with GFCI system and returns True if online """
        return False
    
    def set_enabled(self, value: bool):
        """ Sets whether or not the GFCI breaker is even enabled """
        print(f"DUMMY_DRIVER: Setting enabled state to  {value}")


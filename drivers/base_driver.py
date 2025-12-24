from abc import ABC, abstractmethod
from typing import Type, Dict, Any

class HardwareDriver(ABC):
    _instances: Dict[str, Type] = {}

    def __init__(self, params: Dict[str, Any] = None):
        self.params = params or {}

    @classmethod
    def get_driver(cls, key: str) -> Type:
        """ Turns a string into the specified driver class """
        return cls._instances[key]

    @classmethod
    def register_driver(cls, key: str):
        """ Drivers should use this as a decorator to specify a string-key to use in the db """
        def decorator(subclass):
            cls._instances[key] = subclass
            return subclass
        return decorator
    
    # Backwards compatibility for the typo in previous version
    regster_driver = register_driver

    @abstractmethod
    def hardware_init(self):
        """Initialize the hardware connection.
        This should block until this piece of hardware is ready."""
        pass

    @abstractmethod
    def hardware_deinit(self):
        """Deinitialize the hardware connection.
        This should block until this piece of hardware is fully deinitialized."""
        pass

class BaseSensorDriver(HardwareDriver):
    _instances = {}

    @abstractmethod
    def read(self) -> float:
        """Read the sensor value and return it."""
        pass

class BaseOutputDriver(HardwareDriver):
    _instances = {}

    @abstractmethod
    def set_state(self, state):
        """Set the output state (True/False for relays, etc)."""
        pass
    
    @abstractmethod
    def get_state(self):
        """Get the current state."""
        pass

class BaseLCDDriver(HardwareDriver):
    _instances = {}

    @abstractmethod
    def write_line(self, line_num, text):
        """Write text to a specific line (0-3)."""
        pass

    @abstractmethod
    def clear(self):
        """Clear the display."""
        pass
    
    @abstractmethod
    def set_backlight(self, state):
        """Turn backlight on/off."""
        pass

class BaseGFCIDriver(HardwareDriver):
    _instances = {}

    @abstractmethod
    def set_tolerance(self, value: float):
        """ Sets a new value for fault detection tolerance """
        pass

    @abstractmethod
    def set_threshold(self, value: float):
        """ Sets a new value for fault detection threshold """
        pass

    @abstractmethod
    def ping(self) -> bool:
        """ Checks connection with GFCI system and returns True if online """
    
    @abstractmethod
    def set_enabled(self, value: bool):
        """ Sets whether or not the GFCI breaker is even enabled """
        pass

    @abstractmethod
    def set_tripped(self, circuit: int):
        """ Forces the circuit to trip """
        pass

    @abstractmethod
    def is_tripped(self, circuit: int) -> bool:
        """ Returns True if the GFCI is currently tripped for the specified circuit """
        pass

    @abstractmethod
    def reset_tripped(self, circuit: int):
        """ Forces the circuit to cease to be tripped (circuit 1 or circuit 2) """
        pass

@BaseOutputDriver.register_driver("gfci_relay")
class GFCIRelay(BaseOutputDriver):
    def __init__(self, params=None):
        super().__init__(params)
        self.circuit = int(self.params.get('circuit', 1))

    def hardware_init(self):
        pass

    def hardware_deinit(self):
        pass

    def set_state(self, state):
        from app.hardware import gfci_driver
        from app.dynconfig import DynConfig
        if gfci_driver and DynConfig.gfci_enabled:
            if state:
                gfci_driver.reset_tripped(self.circuit)
            else:
                gfci_driver.set_tripped(self.circuit)

    def get_state(self):
        from app.hardware import gfci_driver
        from app.dynconfig import DynConfig
        if gfci_driver and DynConfig.gfci_enabled:
            return not gfci_driver.is_tripped(self.circuit)
        return False

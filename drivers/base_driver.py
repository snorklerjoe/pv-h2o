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
    def set_tripped(self, circuit: int):
        """ Forces the circuit to trip (circuit 1 or circuit 2) """

    @abstractmethod
    def reset_tripped(self, circuit: int):
        """ Forces the circuit to cease to be tripped (circuit 1 or circuit 2) """

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
        """Initialize the hardware connection."""
        pass

class BaseSensorDriver(HardwareDriver):
    _instances = {}

    @abstractmethod
    def read(self):
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

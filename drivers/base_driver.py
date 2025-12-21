from abc import ABC, abstractmethod
from typing import Type

class BaseSensorDriver(ABC):
    _instances = {}

    def get_driver(key: str) -> Type:
        """ Turns a string into the specified driver class """
        return BaseSensorDriver._instances[key]
    
    def regster_driver(key: str):
        """ Drivers should use this as a decorator to specify a string-key to use in the db """
        def decorator(cls):
            BaseSensorDriver._instances[key] = cls
            return cls
        return decorator

    def __init__(self, params=None):
        self.params = params or {}

    @abstractmethod
    def read(self):
        """Read the sensor value and return it."""
        pass

class BaseOutputDriver(ABC):
    _instances = {}

    def get_driver(key: str) -> Type:
        """ Turns a string into the specified driver class """
        return BaseOutputDriver._instances[key]
    
    def regster_driver(key: str):
        """ Drivers should use this as a decorator to specify a string-key to use in the db """
        def decorator(cls):
            BaseOutputDriver._instances[key] = cls
            return cls
        return decorator

    def __init__(self, params=None):
        self.params = params or {}

    @abstractmethod
    def set_state(self, state):
        """Set the output state (True/False for relays, etc)."""
        pass
    
    @abstractmethod
    def get_state(self):
        """Get the current state."""
        pass

class BaseLCDDriver(ABC):
    _instances = {}

    def get_driver(key: str) -> Type:
        """ Turns a string into the specified driver class """
        return BaseLCDDriver._instances[key]
    
    def regster_driver(key: str):
        """ Drivers should use this as a decorator to specify a string-key to use in the db """
        def decorator(cls):
            BaseLCDDriver._instances[key] = cls
            return cls
        return decorator


    def __init__(self, params=None):
        self.params = params or {}

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

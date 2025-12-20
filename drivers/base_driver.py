from abc import ABC, abstractmethod

class BaseSensorDriver(ABC):
    def __init__(self, params=None):
        self.params = params or {}

    @abstractmethod
    def read(self):
        """Read the sensor value and return it."""
        pass

class BaseOutputDriver(ABC):
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

import time
import threading
import glob
from typing import Dict, Any, List
import numpy as np
from scipy.stats import trim_mean
from loguru import logger

from drivers.base_driver import BaseSensorDriver, BaseOutputDriver, BaseLCDDriver, BaseGFCIDriver

try:
    import smbus2 as smbus
except ImportError:
    try:
        import smbus
    except ImportError:
        smbus = None
        logger.warning("smbus not installed. Real drivers will fail if used.")

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
    logger.warning("RPi.GPIO not installed. Real drivers will fail if used.")
except RuntimeError:
    GPIO = None
    logger.warning("Not on a real raspi. Real drivers will fail if used.")

# --- Arduino Interface ---

class ArduinoInterface:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ArduinoInterface, cls).__new__(cls)
                    cls._instance.initialized = False
        return cls._instance

    def initialize(self, address=0x08, bus_num=1, reset_pin=12):
        with self._lock:
            if self.initialized:
                return
            
            self.address = address
            self.bus_num = bus_num
            self.reset_pin = reset_pin
            
            if smbus:
                try:
                    self.bus = smbus.SMBus(self.bus_num)
                except Exception as e:
                    logger.error(f"Failed to open I2C bus {self.bus_num}: {e}")
                    self.bus = None
            else:
                self.bus = None
                
            if GPIO:
                try:
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setwarnings(False)
                    GPIO.setup(self.reset_pin, GPIO.IN) # Default to input (high impedance)
                except Exception as e:
                    logger.error(f"Failed to setup GPIO: {e}")
            
            self.initialized = True

    def reset_arduino(self):
        logger.info("Resetting Arduino...")
        if GPIO:
            with self._lock:
                GPIO.setup(self.reset_pin, GPIO.OUT)
                GPIO.output(self.reset_pin, GPIO.LOW)
                time.sleep(1)
                GPIO.output(self.reset_pin, GPIO.HIGH)
                GPIO.setup(self.reset_pin, GPIO.IN)
                time.sleep(2)
        else:
            logger.warning("Cannot reset Arduino: GPIO not available")

    def read_word(self, command: int) -> int:
        if not self.bus:
            # Try to re-init? Or just fail.
            logger.error("I2C bus not available")
            return 0
            
        with self._lock:
            samples = []
            # Legacy logic: retry until we get 10 samples, resetting on error
            while len(samples) < 10:
                try:
                    time.sleep(1/25)
                    # The legacy code sends the command as the register address
                    val = self.bus.read_word_data(self.address, command)
                    samples.append(val)
                except (OSError, IOError):
                    logger.warning("I2C Read Error. Resetting Arduino.")
                    self.reset_arduino()
            
            # Legacy: int(trim_mean(array(samples), 0.20)+0.5)
            return int(trim_mean(np.array(samples), 0.20) + 0.5)

    def write_byte(self, command: int):
        if not self.bus:
            logger.error("I2C bus not available")
            return

        with self._lock:
            done = False
            while not done:
                try:
                    # Legacy: bus.write_byte(addr, int(sys.argv[1]))
                    self.bus.write_byte(self.address, command)
                    done = True
                except (OSError, IOError):
                    logger.warning("I2C Write Error. Resetting Arduino.")
                    self.reset_arduino()

# --- Drivers ---

@BaseSensorDriver.register_driver("arduino")
class ArduinoSensorDriver(BaseSensorDriver):
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.command = int(self.params.get('command', 0))
        self.slope = float(self.params.get('slope', 1.0))
        self.intercept = float(self.params.get('intercept', 0.0))
        self.interface = ArduinoInterface()

    def hardware_init(self):
        self.interface.initialize()

    def hardware_deinit(self):
        pass

    def read(self) -> float:
        raw = self.interface.read_word(self.command)
        return raw * self.slope + self.intercept

@BaseOutputDriver.register_driver("arduino")
class ArduinoOutputDriver(BaseOutputDriver):
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.on_command = int(self.params.get('on_command', 0))
        self.off_command = int(self.params.get('off_command', 0))
        self._state = False
        self.interface = ArduinoInterface()

    def hardware_init(self):
        self.interface.initialize()

    def hardware_deinit(self):
        self.set_state(False)

    def set_state(self, state):
        self._state = state
        cmd = self.on_command if state else self.off_command
        self.interface.write_byte(cmd)

    def get_state(self):
        return self._state

@BaseSensorDriver.register_driver("w1_temp_index")
class W1ThermometerIndexDriver(BaseSensorDriver):
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.index = int(self.params.get('index', 0))
        self.base_dir = '/sys/bus/w1/devices/'

    def hardware_init(self):
        pass

    def hardware_deinit(self):
        pass

    def read_temp_raw(self):
        try:
            device_folder = glob.glob(self.base_dir + '28*')[self.index]
            device_file = device_folder + '/w1_slave'
            with open(device_file, 'r') as f:
                lines = f.readlines()
            return lines
        except (IndexError, FileNotFoundError, OSError):
            logger.error(f"W1 device at index {self.index} not found.")
            return []

    def read(self) -> float:
        lines = self.read_temp_raw()
        if not lines:
            return 0.0
            
        if lines[0].strip()[-3:] != 'YES':
            return 0.0
            
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            temp_f = temp_c * 9.0 / 5.0 + 32.0
            return temp_f
            
        return 0.0

@BaseSensorDriver.register_driver("w1_temp")
class W1ThermometerDriver(BaseSensorDriver):
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.device_id = self.params.get('device_id')
        self.base_dir = '/sys/bus/w1/devices/'

    def hardware_init(self):
        pass

    def hardware_deinit(self):
        pass

    def read_temp_raw(self):
        device_file = self.base_dir + self.device_id + '/w1_slave'
        try:
            with open(device_file, 'r') as f:
                lines = f.readlines()
            return lines
        except FileNotFoundError:
            logger.error(f"W1 device {self.device_id} not found.")
            return []

    def read(self) -> float:
        if not self.device_id:
            return 0.0
            
        lines = self.read_temp_raw()
        if not lines:
            return 0.0
            
        # Wait for YES
        # Legacy code didn't show this part but it's standard W1
        # If the first line doesn't end with YES, we might need to retry?
        # Standard python implementation usually loops.
        
        if lines[0].strip()[-3:] != 'YES':
            # Try reading again? Or just return error?
            # For now, just return 0 or last known?
            return 0.0
            
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            temp_f = temp_c * 9.0 / 5.0 + 32.0
            return temp_f # Legacy system seemed to use F based on LCD output "Temp(F)"
            
        return 0.0

# --- LCD Driver ---

# LCD Constants
LCD_CLEARDISPLAY = 0x01
LCD_RETURNHOME = 0x02
LCD_ENTRYMODESET = 0x04
LCD_DISPLAYCONTROL = 0x08
LCD_FUNCTIONSET = 0x20

LCD_ENTRYLEFT = 0x02
LCD_DISPLAYON = 0x04
LCD_2LINE = 0x08
LCD_5x8DOTS = 0x00
LCD_4BITMODE = 0x00 # Note: Legacy code had 0x00 for 4BITMODE? Wait.
# Legacy: LCD_4BITMODE = 0x00. 
# Usually 4bit is 0x00 in the function set command if DL is bit 4.
# DL=1 (8bit) is 0x10. DL=0 (4bit) is 0x00. Correct.

LCD_BACKLIGHT = 0x08
LCD_NOBACKLIGHT = 0x00

En = 0b00000100 # Enable bit
Rw = 0b00000010 # Read/Write bit
Rs = 0b00000001 # Register select bit

@BaseLCDDriver.register_driver("i2c_lcd")
class I2CLCDDriver(BaseLCDDriver):
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.address = int(self.params.get('address', 0x27))
        self.bus_num = int(self.params.get('bus_num', 1))
        self.bus = None

    def hardware_init(self):
        if smbus:
            try:
                self.bus = smbus.SMBus(self.bus_num)
                self._init_lcd()
            except Exception as e:
                logger.error(f"Failed to init LCD: {e}")

    def _write_cmd(self, cmd):
        if self.bus:
            self.bus.write_byte(self.address, cmd)
            time.sleep(0.0001)

    def _lcd_strobe(self, data):
        # self.lcd_device.write_cmd(data | En | LCD_BACKLIGHT)
        self._write_cmd(data | En | LCD_BACKLIGHT)
        time.sleep(.0005)
        # self.lcd_device.write_cmd(((data & ~En) | LCD_BACKLIGHT))
        self._write_cmd(((data & ~En) | LCD_BACKLIGHT))
        time.sleep(.0001)

    def _lcd_write_four_bits(self, data):
        self._write_cmd(data | LCD_BACKLIGHT)
        self._lcd_strobe(data)

    def _lcd_write(self, cmd, mode=0):
        self._lcd_write_four_bits(mode | (cmd & 0xF0))
        self._lcd_write_four_bits(mode | ((cmd << 4) & 0xF0))

    def _init_lcd(self):
        # Initialization sequence from legacy code
        self._lcd_write(0x03)
        self._lcd_write(0x03)
        self._lcd_write(0x03)
        self._lcd_write(0x02)

        self._lcd_write(LCD_FUNCTIONSET | LCD_2LINE | LCD_5x8DOTS | LCD_4BITMODE)
        self._lcd_write(LCD_DISPLAYCONTROL | LCD_DISPLAYON)
        self._lcd_write(LCD_CLEARDISPLAY)
        self._lcd_write(LCD_ENTRYMODESET | LCD_ENTRYLEFT)
        time.sleep(0.2)

    def hardware_deinit(self):
        self.clear()
        self.set_backlight(False)

    def write_line(self, line_num, text):
        if not self.bus: return
        
        # Line addresses
        if line_num == 0: # 1-based in legacy, 0-based in base driver?
            # BaseLCDDriver says 0-3.
            # Legacy: 1->0x80, 2->0xC0, 3->0x94, 4->0xD4
            addr = 0x80
        elif line_num == 1:
            addr = 0xC0
        elif line_num == 2:
            addr = 0x94
        elif line_num == 3:
            addr = 0xD4
        else:
            return

        self._lcd_write(addr)
        
        for char in text:
            self._lcd_write(ord(char), Rs)

    def clear(self):
        if not self.bus: return
        self._lcd_write(LCD_CLEARDISPLAY)
        self._lcd_write(LCD_RETURNHOME)

    def set_backlight(self, state):
        if not self.bus: return
        if state:
            self._write_cmd(LCD_BACKLIGHT)
        else:
            self._write_cmd(LCD_NOBACKLIGHT)


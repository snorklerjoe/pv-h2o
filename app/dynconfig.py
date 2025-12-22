""" Dynamic configuration from the database """

from app.models import SystemConfig
from app.hardware_constants import SensorId, RelayId
from app.utils import classproperty
from loguru import logger
from typing import Callable, Any
from enum import Enum

class MalformedConfigException(ValueError):
    pass

class ConfigCategory(Enum):
    REGULATION = "Regulation"
    LOCATION = "Location & Time"
    GFCI = "GFCI Control"
    WATCHDOG = "Watchdog & Safety"
    NOTIFICATIONS = "Notifications"
    DRIVERS = "Hardware Drivers"
    SYSTEM = "System"
    MISC = "Miscellaneous"

# Global definitions storage to avoid circular reference during class creation
_definitions = {}

def conf_property(key: str, default: str, description: str = "", category: ConfigCategory = ConfigCategory.SYSTEM, validator: Callable[[str], bool] = lambda x: True, value_type: str = "text"):
    """
    Creates a property that looks up 'key' in 'self.confDict'.
    If missing, returns 'default'.
    """
    def getter(cls):
        return cls._confDict.get(key, default)
    
    # Register description
    _definitions[key] = {
        "default": default,
        "description": description,
        "category": category.value,
        "is_eval": False,
        "validator": validator,
        "value_type": value_type
    }
    
    return classproperty(getter)

def conf_property_evald(key: str, default: str, description: str = "", category: ConfigCategory = ConfigCategory.SYSTEM, validator: Callable[[Any], bool] = lambda x: True, value_type: str = "text"):
    """
    The same as `conf_property`, but where the value is evaluated as Python code
    """
    def getter(cls):
        strval: str = cls._confDict.get(key, default)
        try:
            return eval(strval)
        except Exception as e:
            raise MalformedConfigException(e)

    # Register description
    _definitions[key] = {
        "default": default,
        "description": description,
        "category": category.value,
        "is_eval": True,
        "validator": validator,
        "value_type": value_type
    }

    return classproperty(getter)

class DynConfig:
    _confDict = None
    _definitions = _definitions  # Stores metadata about config properties

    @classmethod
    def validate(cls, key, value):
        if key not in cls._definitions:
            return False
        
        defn = cls._definitions[key]
        validator = defn['validator']
        
        # If it's an eval'd property, we might need to eval the value first if it's coming in as a string from the API
        # But the API might send it as a typed JSON object if it's a boolean or number.
        # However, the database stores strings.
        # The validator should probably check the *evaluated* value for eval'd properties.
        
        val_to_check = value
        if defn['is_eval'] and isinstance(value, str):
             try:
                 val_to_check = eval(value)
             except:
                 return False
        
        try:
            return validator(val_to_check)
        except:
            return False

    @classmethod
    def register_property(cls, key, default, description, is_eval, category=ConfigCategory.SYSTEM, validator=lambda x: True, value_type="text"):
        cls._definitions[key] = {
            "default": default,
            "description": description,
            "category": category.value,
            "is_eval": is_eval,
            "validator": validator,
            "value_type": value_type
        }

    @classmethod
    def get_definitions(cls):
        return cls._definitions

    @classmethod
    def get_raw_config(cls):
        """ Returns the raw configuration dictionary (strings) as stored in DB """
        return cls._confDict

    @classmethod
    def fetch_config(cls):
        # Grab latest config dictionary from the database
        # This requires an active application context
        try:
            pairs = SystemConfig.query.all()
            DynConfig._confDict = {pair.key: pair.value for pair in pairs}
            logger.info("Loaded dynamic configuration from the database")
        except Exception:
            logger.error("Error while loading dynamic configuration from the database")
            # Fallback if DB is not ready or context missing (e.g. during tests setup)
            DynConfig._confDict = {}

    @classproperty    
    def initialized(cls):
        return cls._confDict is not None

    @classmethod
    def reload(self):
        """Refreshes the configuration from the database."""
        try:
            pairs = SystemConfig.query.all()
            DynConfig._confDict = {pair.key: pair.value for pair in pairs}
            logger.info("Re-loaded dynamic configuration from the database")
        except Exception:
            logger.error("Error while re-loading dynamic config from the database")

    # NOTE: ALL TEMPERATURES ARE IN DEG F

    # Regulation
    manual_mode = conf_property_evald("manual_mode", "False", "Enable manual mode to override automatic regulation", ConfigCategory.REGULATION, lambda x: isinstance(x, bool), "boolean")
    regulator_night_override = conf_property_evald("regulator_night_override", "False", "Keep regulator running at night", ConfigCategory.REGULATION, lambda x: isinstance(x, bool), "boolean")
    target_temp_tank1_f = conf_property_evald("target_temp_tank1_f", "140.0", "Target temperature for Tank 1 (F)", ConfigCategory.REGULATION, lambda x: isinstance(x, (int, float)) and 0 <= x <= 212, "number")
    target_temp_tank2_f = conf_property_evald("target_temp_tank2_f", "140.0", "Target temperature for Tank 2 (F)", ConfigCategory.REGULATION, lambda x: isinstance(x, (int, float)) and 0 <= x <= 212, "number")
    temp_hysteresis = conf_property_evald("temp_hysteresis", "2.0", "Temperature hysteresis (F)", ConfigCategory.REGULATION, lambda x: isinstance(x, (int, float)) and x > 0, "number")
    polling_rate_seconds = conf_property_evald("polling_rate_seconds", "60", "Sensor polling rate in seconds", ConfigCategory.REGULATION, lambda x: isinstance(x, int) and x > 0, "number")

    circuit_states = conf_property_evald("circuit_states", "[False, False]", "Manual circuit states [Circ1, Circ2]", ConfigCategory.REGULATION, lambda x: isinstance(x, list) and len(x) == 2, "json")

    # Location & Day/Night
    location_name = conf_property("location_name", "Concord", "Name of the location", ConfigCategory.LOCATION, lambda x: len(x) > 0, "text")
    location_lat = conf_property_evald("location_lat", "0.0", "Latitude", ConfigCategory.LOCATION, lambda x: isinstance(x, (int, float)) and -90 <= x <= 90, "number")
    location_long = conf_property_evald("location_long", "0.0", "Longitude", ConfigCategory.LOCATION, lambda x: isinstance(x, (int, float)) and -180 <= x <= 180, "number")
    sunrise_offset_minutes = conf_property_evald("sunrise_offset_minutes", "30", "Minutes after sunrise to enable circuits", ConfigCategory.LOCATION, lambda x: isinstance(x, int), "number")
    sunset_offset_minutes = conf_property_evald("sunset_offset_minutes", "30", "Minutes before sunset to disable circuits", ConfigCategory.LOCATION, lambda x: isinstance(x, int), "number")

    # GFCI Control
    gfci_esp32_ip = conf_property("gfci_esp32_ip", "192.168.1.100", "IP Address of GFCI ESP32", ConfigCategory.GFCI, lambda x: True, "text")
    gfci_response_factor = conf_property_evald("gfci_response_factor", "1.0", "GFCI Response Factor", ConfigCategory.GFCI, lambda x: isinstance(x, (int, float)) and x > 0, "number")
    gfci_trip_threshold_ma = conf_property_evald("gfci_trip_threshold_ma", "5.0", "GFCI Trip Threshold (mA)", ConfigCategory.GFCI, lambda x: isinstance(x, (int, float)) and x > 0, "number")
    gfci_enabled = conf_property_evald("gfci_enabled", "True", "Whether the GFCI breakers are even enabled", ConfigCategory.REGULATION, lambda x: isinstance(x, bool), "boolean")

    # Watchdog
    watchdog_excludes = conf_property_evald("watchdog_excludes", "[]", "List of disabled watchdog triggers", ConfigCategory.WATCHDOG, lambda x: isinstance(x, list), "json")
    trip_current_max_amps = conf_property_evald("trip_current_max_amps", "20.0", "Max current before trip (Amps)", ConfigCategory.WATCHDOG, lambda x: isinstance(x, (int, float)) and x > 0, "number")
    trip_temp_max_f = conf_property_evald("trip_temp_max_f", "200.0", "Max temperature before trip (F)", ConfigCategory.WATCHDOG, lambda x: isinstance(x, (int, float)) and 0 <= x <= 250, "number")
    trip_impedance_min_ohms = conf_property_evald("trip_impedance_min_ohms", "10.0", "Min impedance before trip (Ohms)", ConfigCategory.WATCHDOG, lambda x: isinstance(x, (int, float)) and x >= 0, "number")
    trip_leakage_threshold_amps = conf_property_evald("trip_leakage_threshold_amps", "0.75", "Leakage current threshold (Amps)", ConfigCategory.WATCHDOG, lambda x: isinstance(x, (int, float)) and x >= 0, "number")

    # Notifications
    notify_email_enabled = conf_property_evald("notify_email_enabled", "False", "Enable email notifications", ConfigCategory.NOTIFICATIONS, lambda x: isinstance(x, bool), "boolean")
    notify_email_recipient = conf_property("notify_email_recipient", "", "Recipient email address", ConfigCategory.NOTIFICATIONS, lambda x: True, "text")
    notify_smtp_server = conf_property("notify_smtp_server", "", "SMTP Server Address", ConfigCategory.NOTIFICATIONS, lambda x: True, "text")
    notify_smtp_port = conf_property_evald("notify_smtp_port", "587", "SMTP Server Port", ConfigCategory.NOTIFICATIONS, lambda x: isinstance(x, int) and x > 0, "number")
    notify_smtp_user = conf_property("notify_smtp_user", "", "SMTP Username", ConfigCategory.NOTIFICATIONS, lambda x: True, "text")
    notify_smtp_pass = conf_property("notify_smtp_pass", "", "SMTP Password", ConfigCategory.NOTIFICATIONS, lambda x: True, "text")
    notify_to_emails = conf_property("notify_to_emails", "john@example.com,bob@example.com", "Comma-separated list of notification emails", ConfigCategory.NOTIFICATIONS, lambda x: True, "text")

    # Drivers for things
    driver_sensors = conf_property_evald("driver_sensors", "{" + ', '.join([f"\"{key.value}\":(\"dummy\", {{ 'value': 2.0, 'noise': 1.0 }})" for key in SensorId]) + "}", "Sensor Driver Configuration; note that drivers do not update until restart.", ConfigCategory.DRIVERS, lambda x: isinstance(x, dict), "json")
    driver_relays = conf_property_evald("driver_relays", "{" + ', '.join([f"\"{key.value}\":(\"gfci_relay\", {{ 'circuit': {1 if key.value == 'gfci1' else 2} }})" if key.value.startswith('gfci') else f"\"{key.value}\":(\"dummy\", {{ }})" for key in RelayId]) + "}", "Relay Driver Configuration", ConfigCategory.DRIVERS, lambda x: isinstance(x, dict), "json")
    driver_lcd = conf_property_evald("driver_lcd", "(\"dummy\", {})", "LCD Driver Configuration", ConfigCategory.DRIVERS, lambda x: isinstance(x, dict), "text")
    driver_gfci = conf_property_evald("driver_gfci", "(\"dummy\", {})", "GFCI Driver Configuration", ConfigCategory.DRIVERS, lambda x: isinstance(x, dict), "text")

    # Misc
    lcd_status_period = conf_property_evald("lcd_status_period", "8", "Seconds for which each status screen is up on the status LCD", ConfigCategory.MISC, lambda x: isinstance(x, int), "number")

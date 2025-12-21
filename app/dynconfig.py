""" Dynamic configuration from the database """

from app.models import SystemConfig
from app.hardware_constants import SensorId, RelayId
from app.utils import classproperty
from loguru import logger

class MalformedConfigException(ValueError):
    pass

# Global definitions storage to avoid circular reference during class creation
_definitions = {}

def conf_property(key: str, default: str, description: str = ""):
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
        "is_eval": False
    }
    
    return classproperty(getter)

def conf_property_evald(key: str, default: str, description: str = ""):
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
        "is_eval": True
    }

    return classproperty(getter)

class DynConfig:
    _confDict = None
    _definitions = _definitions  # Stores metadata about config properties

    @classmethod
    def register_property(cls, key, default, description, is_eval):
        cls._definitions[key] = {
            "default": default,
            "description": description,
            "is_eval": is_eval
        }

    @classmethod
    def get_definitions(cls):
        return cls._definitions

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
    manual_mode = conf_property_evald("manual_mode", "False", "Enable manual mode to override automatic regulation")
    target_temp_tank1_f = conf_property_evald("target_temp_tank1_f", "140.0", "Target temperature for Tank 1 (F)")
    target_temp_tank2_f = conf_property_evald("target_temp_tank2_f", "140.0", "Target temperature for Tank 2 (F)")
    temp_hysteresis = conf_property_evald("temp_hysteresis", "2.0", "Temperature hysteresis (F)")
    polling_rate_seconds = conf_property_evald("polling_rate_seconds", "60", "Sensor polling rate in seconds")

    circuit_states = conf_property_evald("circuit_states", "[False, False]", "Manual circuit states [Circ1, Circ2]")

    # Location & Day/Night
    location_name = conf_property("location_name", "Concord", "Name of the location")
    location_lat = conf_property_evald("location_lat", "0.0", "Latitude")
    location_long = conf_property_evald("location_long", "0.0", "Longitude")
    sunrise_offset_minutes = conf_property_evald("sunrise_offset_minutes", "30", "Minutes after sunrise to enable circuits")
    sunset_offset_minutes = conf_property_evald("sunset_offset_minutes", "30", "Minutes before sunset to disable circuits")

    # GFCI Control
    gfci_esp32_ip = conf_property("gfci_esp32_ip", "192.168.1.100", "IP Address of GFCI ESP32")
    gfci_response_factor = conf_property_evald("gfci_response_factor", "1.0", "GFCI Response Factor")
    gfci_trip_threshold_ma = conf_property_evald("gfci_trip_threshold_ma", "5.0", "GFCI Trip Threshold (mA)")

    # Watchdog
    trip_current_max_amps = conf_property_evald("trip_current_max_amps", "15.0", "Max current before trip (Amps)")
    trip_temp_max_f = conf_property_evald("trip_temp_max_f", "200.0", "Max temperature before trip (F)")
    trip_impedance_min_ohms = conf_property_evald("trip_impedance_min_ohms", "10.0", "Min impedance before trip (Ohms)")
    trip_leakage_threshold_amps = conf_property_evald("trip_leakage_threshold_amps", "0.1", "Leakage current threshold (Amps)")

    # Notifications
    notify_email_enabled = conf_property_evald("notify_email_enabled", "False", "Enable email notifications")
    notify_email_recipient = conf_property("notify_email_recipient", "", "Recipient email address")
    notify_smtp_server = conf_property("notify_smtp_server", "", "SMTP Server Address")
    notify_smtp_port = conf_property_evald("notify_smtp_port", "587", "SMTP Server Port")
    notify_smtp_user = conf_property("notify_smtp_user", "", "SMTP Username")
    notify_smtp_pass = conf_property("notify_smtp_pass", "", "SMTP Password")
    notify_to_emails = conf_property("notify_to_emails", "john@example.com,bob@example.com", "Comma-separated list of notification emails")

    # Drivers for things
    driver_sensors = conf_property_evald("driver_sensors", "{" + ', '.join([f"\"{key.value}\":(\"dummy\", {{ 'value': 2.0, 'noise': 1.0 }})" for key in SensorId]) + "}", "Sensor Driver Configuration")
    driver_relays = conf_property_evald("driver_relays", "{" + ', '.join([f"\"{key.value}\":(\"dummy\", {{ }})" for key in RelayId]) + "}", "Relay Driver Configuration")
    driver_lcd = conf_property("driver_lcd", "(dummy, {})", "LCD Driver Configuration")
    driver_gfci = conf_property("driver_gfci", "(dummy, {})", "GFCI Driver Configuration")

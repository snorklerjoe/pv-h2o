""" Dynamic configuration from the database """

from app.models import SystemConfig
from app.hardware_constants import SensorId, RelayId
from app.utils import classproperty
from loguru import logger

class MalformedConfigException(ValueError):
    pass

def conf_property(key: str, default: str):
    """
    Creates a property that looks up 'key' in 'self.confDict'.
    If missing, returns 'default'.
    """
    def getter(cls):
        return cls._confDict.get(key, default)
    return classproperty(getter)

def conf_property_evald(key: str, default: str):
    """
    The same as `conf_property`, but where the value is evaluated as Python code
    """
    def getter(cls):
        strval: str = cls._confDict.get(key, default)
        try:
            return eval(strval)
        except Exception as e:
            raise MalformedConfigException(e)
    return classproperty(getter)

class DynConfig:
    _confDict = None

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
    manual_mode = conf_property_evald("manual_mode", "False")  # Regulation does not happen in manual mode
    target_temp_tank1_f = conf_property_evald("target_temp_tank1_f", "140.0")
    target_temp_tank2_f = conf_property_evald("target_temp_tank2_f", "140.0")
    temp_hysteresis = conf_property_evald("temp_hysteresis", "2.0")
    polling_rate_seconds = conf_property_evald("polling_rate_seconds", "60")

    circuit_states = conf_property_evald("circuit_states", "[False, False]")

    # Location & Day/Night
    location_name = conf_property("location_name", "Concord")
    location_lat = conf_property_evald("location_lat", "0.0")
    location_long = conf_property_evald("location_long", "0.0")
    sunrise_offset_minutes = conf_property_evald("sunrise_offset_minutes", "30")
    sunset_offset_minutes = conf_property_evald("sunset_offset_minutes", "30")

    # GFCI Control
    gfci_esp32_ip = conf_property("gfci_esp32_ip", "192.168.1.100")
    gfci_response_factor = conf_property_evald("gfci_response_factor", "1.0")
    gfci_trip_threshold_ma = conf_property_evald("gfci_trip_threshold_ma", "5.0")

    # Watchdog
    trip_current_max_amps = conf_property_evald("trip_current_max_amps", "15.0")
    trip_temp_max_f = conf_property_evald("trip_temp_max_f", "200.0")
    trip_impedance_min_ohms = conf_property_evald("trip_impedance_min_ohms", "10.0")
    trip_leakage_threshold_amps = conf_property_evald("trip_leakage_threshold_amps", "0.1")

    # Notifications
    notify_email_enabled = conf_property_evald("notify_email_enabled", "False")
    notify_email_recipient = conf_property("notify_email_recipient", "")
    notify_smtp_server = conf_property("notify_smtp_server", "")
    notify_smtp_port = conf_property_evald("notify_smtp_port", "587")
    notify_smtp_user = conf_property("notify_smtp_user", "")
    notify_smtp_pass = conf_property("notify_smtp_pass", "")
    notify_to_emails = conf_property("notify_to_emails", "john@example.com,bob@example.com")

    # Drivers for things
    driver_sensors = conf_property_evald("driver_sensors", "{" + ', '.join([f"\"{key.value}\":(\"dummy\", {{ 'value': 2.0, 'noise': 1.0 }})" for key in SensorId]) + "}")
    driver_relays = conf_property_evald("driver_relays", "{" + ', '.join([f"\"{key.value}\":(\"dummy\", {{ }})" for key in RelayId]) + "}")
    driver_lcd = conf_property("driver_lcd", "(dummy, {})")
    driver_gfci = conf_property("driver_gfci", "(dummy, {})")

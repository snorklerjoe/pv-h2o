""" Dynamic configuration from the database """

from app.models import SystemConfig

def conf_property(key: str, default: str):
    """
    Creates a property that looks up 'key' in 'self.confDict'.
    If missing, returns 'default'.
    """
    def getter(self):
        return self.confDict.get(key, default)
    return property(getter)

class DynConfig:
    def __init__(self):
        # Grab latest config dictionary from the database
        # This requires an active application context
        try:
            pairs = SystemConfig.query.all()
            self.confDict = {pair.key: pair.value for pair in pairs}
        except Exception:
            # Fallback if DB is not ready or context missing (e.g. during tests setup)
            self.confDict = {}

    def reload(self):
        """Refreshes the configuration from the database."""
        try:
            pairs = SystemConfig.query.all()
            self.confDict = {pair.key: pair.value for pair in pairs}
        except Exception:
            pass

    # NOTE: ALL TEMPERATURES ARE IN DEG F

    # Regulation
    manual_mode = conf_property("manual_mode", "False")  # Regulation does not happen in manual mode
    target_temp_tank1_f = conf_property("target_temp_tank1_f", "140.0")
    target_temp_tank2_f = conf_property("target_temp_tank2_f", "140.0")
    temp_hysteresis = conf_property("temp_hysteresis", "2.0")
    polling_rate_seconds = conf_property("polling_rate_seconds", "60")

    # Location & Day/Night
    location_name = conf_property("location_name", "Concord")
    location_lat = conf_property("location_lat", "0.0")
    location_long = conf_property("location_long", "0.0")
    sunrise_offset_minutes = conf_property("sunrise_offset_minutes", "30")
    sunset_offset_minutes = conf_property("sunset_offset_minutes", "30")

    # GFCI Control
    gfci_esp32_ip = conf_property("gfci_esp32_ip", "192.168.1.100")
    gfci_response_factor = conf_property("gfci_response_factor", "1.0")
    gfci_trip_threshold_ma = conf_property("gfci_trip_threshold_ma", "5.0")

    # Watchdog
    trip_current_max_amps = conf_property("trip_current_max_amps", "15.0")
    trip_temp_max_f = conf_property("trip_temp_max_f", "200.0")
    trip_impedance_min_ohms = conf_property("trip_impedance_min_ohms", "10.0")
    trip_leakage_threshold_amps = conf_property("trip_leakage_threshold_amps", "0.1")

    # Notifications
    notify_email_enabled = conf_property("notify_email_enabled", "false")
    notify_email_recipient = conf_property("notify_email_recipient", "")
    notify_smtp_server = conf_property("notify_smtp_server", "")
    notify_smtp_port = conf_property("notify_smtp_port", "587")
    notify_smtp_user = conf_property("notify_smtp_user", "")
    notify_smtp_pass = conf_property("notify_smtp_pass", "")

    # Drivers


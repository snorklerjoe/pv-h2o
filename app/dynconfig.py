""" Dynamic configuration from the database """

from app.models import SystemConfig

def confProperty(key: str, default: str):
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
    manual_mode = confProperty("manual_mode", "False")  # Regulation does not happen in manual mode
    target_temp_tank1_f = confProperty("target_temp_tank1_f", "140.0")
    target_temp_tank2_f = confProperty("target_temp_tank2_f", "140.0")
    temp_hysteresis = confProperty("temp_hysteresis", "2.0")
    polling_rate_seconds = confProperty("polling_rate_seconds", "60")

    # Location & Day/Night
    location_name = confProperty("location_name", "Concord")
    location_lat = confProperty("location_lat", "0.0")
    location_long = confProperty("location_long", "0.0")
    sunrise_offset_minutes = confProperty("sunrise_offset_minutes", "30")
    sunset_offset_minutes = confProperty("sunset_offset_minutes", "30")

    # GFCI Control
    gfci_esp32_ip = confProperty("gfci_esp32_ip", "192.168.1.100")
    gfci_response_factor = confProperty("gfci_response_factor", "1.0")
    gfci_trip_threshold_ma = confProperty("gfci_trip_threshold_ma", "5.0")

    # Watchdog
    trip_current_max_amps = confProperty("trip_current_max_amps", "15.0")
    trip_temp_max_f = confProperty("trip_temp_max_f", "200.0")
    trip_impedance_min_ohms = confProperty("trip_impedance_min_ohms", "10.0")
    trip_leakage_threshold_amps = confProperty("trip_leakage_threshold_amps", "0.1")

    # Notifications
    notify_email_enabled = confProperty("notify_email_enabled", "false")
    notify_email_recipient = confProperty("notify_email_recipient", "")
    notify_smtp_server = confProperty("notify_smtp_server", "")
    notify_smtp_port = confProperty("notify_smtp_port", "587")
    notify_smtp_user = confProperty("notify_smtp_user", "")
    notify_smtp_pass = confProperty("notify_smtp_pass", "")

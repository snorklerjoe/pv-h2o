""" Contains code pertaining to overall maintenance of system homeostasis. :) """

from .hardwarestate import HardwareState
from .sunrise import get_sun_rise_set_time_today
from .dynconfig import DynConfig
from datetime import timedelta, datetime
from .hardware_constants import RelayId, SensorId
from threading import Thread
from time import sleep
from config import Config
from loguru import logger
from flask import current_app

class Regulator:
    """ Singleton that handles overall regulation of things """
    
    # Implement singleton pattern
    _instance = None
    _initialized = False
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not Regulator._initialized:
            self._status_repr = "~ Regulator hook not yet executed. ~"
            self._thread: Thread | None = None
            Regulator._initialized = True

    def start_regulation(self, app):
        def loop():
            with app.app_context():
                from loguru import logger
                logger.info("Starting regulation loop")
                regulator = Regulator()
                sleep(DynConfig.polling_rate_seconds * 1.5)
                while True:
                    try:
                        logger.debug("Running regulator hook...")
                        regulator.hook()
                        logger.debug("Ran regulator hook.")
                    except Exception as e:
                        logger.exception("Error in regulation loop")
                    sleep(DynConfig.polling_rate_seconds)
        
        logger.info("Creating regulation thread.")
        self._thread = Thread(target=loop, name="Regulation Loop", daemon=True)
        self._thread.start()

    def _is_light_out(self):  # TODO: Cache sunrise / sunset window for the whole day or for the hour or something
        sunrise, sunset = get_sun_rise_set_time_today()
        rise_delta = timedelta(minutes=DynConfig.sunrise_offset_minutes)
        set_delta = timedelta(minutes=DynConfig.sunset_offset_minutes)
        window = (sunrise + rise_delta, sunset - set_delta)
        return window[0] < datetime.now(Config.TIMEZONE) < window[1]

    def get_status_str(self) -> str:
        """ Returns a human-readable string describing the current regulation "decision" """
        return self._status_repr

    def hook(self):
        """ Runs through sensor measurements and does all necessary regulation. """
        if DynConfig.manual_mode:
            self._status_repr = "Manual mode => No regulator action."
            return

        # Handle things if it is night
        if not self._is_light_out():
            self._status_repr = "It's dark out => Circuits are off."
            # Turn everything off, it's night time
            for relay in RelayId:
                HardwareState.set_relay(relay, False)
            return  # no more until the morning.

        # Circuit 1 regulation
        if DynConfig.circuit_states[0]:  # If circuit is "turned on"
            # Check temperature
            reading = HardwareState.cur_sensor_values[SensorId.t1]
            if reading is None:
                self._status_repr = "C1:  Bad/nonexistent sensor reading."
                HardwareState.set_relay(RelayId.circ1, False)
            else:
                current_temp = reading.cald
                target_temp = DynConfig.target_temp_tank1_f
                hysteresis = DynConfig.temp_hysteresis
                
                if current_temp < (target_temp - hysteresis):
                    self._status_repr = "C1:  Fell below target-hysteresis => Circuit ON."
                    HardwareState.set_relay(RelayId.circ1, True)
                elif current_temp > target_temp:
                    self._status_repr = "C1:  Above target temp => Circuit OFF."
                    HardwareState.set_relay(RelayId.circ1, False)
        else:
            self._status_repr = "C1:  Disabled => Circuit OFF."
            HardwareState.set_relay(RelayId.circ1, False)

        self._status_repr += "\n"


        # Circuit 2 regulation
        if DynConfig.circuit_states[1]:  # If circuit is "turned on"
            # Check temperature
            reading = HardwareState.cur_sensor_values[SensorId.t2]
            if reading is None:
                self._status_repr += "C2:  Bad/nonexistent sensor reading."
                HardwareState.set_relay(RelayId.circ2, False)
            else:
                current_temp = reading.cald
                target_temp = DynConfig.target_temp_tank2_f
                hysteresis = DynConfig.temp_hysteresis
                
                if current_temp < (target_temp - hysteresis):
                    self._status_repr += "C2:  Fell below target-hysteresis => Circuit ON."
                    HardwareState.set_relay(RelayId.circ2, True)
                elif current_temp > target_temp:
                    self._status_repr += "C2:  Above target temp => Circuit OFF."
                    HardwareState.set_relay(RelayId.circ2, False)
        else:
            self._status_repr += "C2:  Disabled => Circuit OFF."
            HardwareState.set_relay(RelayId.circ2, False) 

""" Contains code pertaining to overall maintenance of system homeostasis. :) """

from .hardwarestate import HardwareState
from .sunrise import light_window
from .dynconfig import DynConfig
from datetime import datetime
from .hardware_constants import RelayId, SensorId
from threading import Thread
from time import sleep
from app.config import Config
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
            Regulator._initialized = True

    def schedule_regulation(self, app):
        from app import scheduler
        from app.utils import run_with_timeout_and_kill

        def job():
            def task():
                with app.app_context():
                    logger.debug("Running regulation hook.")
                    self.hook()

            run_with_timeout_and_kill(
                task,
                timeout=DynConfig.polling_rate_seconds
            )
        
        if scheduler.get_job('regulation_loop'):
            scheduler.remove_job('regulation_loop')

        scheduler.add_job(
            id='regulation_loop',
            func=job,
            trigger='interval',
            seconds=DynConfig.polling_rate_seconds,
            max_instances=1,
            coalesce=True
        )

    def _is_light_out(self):  # TODO: Cache sunrise / sunset window for the whole day or for the hour or something
        window = light_window()
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
        if not self._is_light_out() and not DynConfig.regulator_night_override:
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
                self._status_repr1 = "C1:  Bad/nonexistent sensor reading."
                HardwareState.set_relay(RelayId.circ1, False)
            else:
                current_temp = reading.cald
                target_temp = DynConfig.target_temp_tank1_f
                hysteresis = DynConfig.temp_hysteresis
                
                if current_temp < (target_temp - hysteresis):
                    self._status_repr1 = "C1:  Fell below target-hysteresis => Circuit ON."
                    HardwareState.set_relay(RelayId.circ1, True)
                elif current_temp > target_temp:
                    self._status_repr1 = "C1:  Above target temp => Circuit OFF."
                    HardwareState.set_relay(RelayId.circ1, False)
        else:
            self._status_repr1 = "C1:  Disabled => Circuit OFF."
            HardwareState.set_relay(RelayId.circ1, False)

        self._status_repr1 += "\n"

        # Circuit 2 regulation
        if DynConfig.circuit_states[1]:  # If circuit is "turned on"
            # Check temperature
            reading = HardwareState.cur_sensor_values[SensorId.t2]
            if reading is None:
                self._status_repr1 += "C2:  Bad/nonexistent sensor reading."
                HardwareState.set_relay(RelayId.circ2, False)
            else:
                current_temp = reading.cald
                target_temp = DynConfig.target_temp_tank2_f
                hysteresis = DynConfig.temp_hysteresis
                
                if current_temp < (target_temp - hysteresis):
                    self._status_repr1 += "C2:  Fell below target-hysteresis => Circuit ON."
                    HardwareState.set_relay(RelayId.circ2, True)
                elif current_temp > target_temp:
                    self._status_repr1 += "C2:  Above target temp => Circuit OFF."
                    HardwareState.set_relay(RelayId.circ2, False)
        else:
            self._status_repr1 += "C2:  Disabled => Circuit OFF."
            HardwareState.set_relay(RelayId.circ2, False) 

        self._status_repr = self._status_repr1 + f"\n\nLast updated {datetime.now(Config.TIMEZONE).isoformat()}"

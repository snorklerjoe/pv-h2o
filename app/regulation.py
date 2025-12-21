""" Contains code pertaining to overall maintenance of system homeostasis. :) """

from .hardwarestate import HardwareState
from .sunrise import get_sun_rise_set_time_today
from .dynconfig import DynConfig
from datetime import timedelta, datetime
from .hardware_constants import RelayId, SensorId
from threading import Thread
from time import sleep

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
        pass

    @staticmethod
    def start_regulation():
        def loop():
            regulator = Regulator()
            while True:
                try:
                    regulator.hook()
                    sleep(DynConfig.polling_rate_seconds)
                except Exception as e:
                    from loguru import logger
                    logger.exception("Error in regulation loop")
                sleep(DynConfig.polling_rate_seconds)
        
        thread = Thread(target=loop, name="Regulation Loop", daemon=True)
        thread.start()

    def _is_light_out(self):  # TODO: Cache sunrise / sunset window for the whole day or for the hour or something
        sunrise, sunset = get_sun_rise_set_time_today()
        rise_delta = timedelta(minutes=DynConfig.sunrise_offset_minutes)
        set_delta = timedelta(minutes=DynConfig.sunset_offset_minutes)
        window = (sunrise + rise_delta, sunset - set_delta)
        return window[0] < datetime.now() < window[1]


    def hook(self):
        """ Runs through sensor measurements and does all necessary regulation. """

        # Don't touch watchdog -- it already runs on its own thread
        # WatchdogTrigger.check_all()
        # if WatchdogTrigger.is_tripped:
        #     # Ensure everything is off
        #     for relay in RelayId:
        #         HardwareState.set_relay(relay, False)
        #     return

        if DynConfig.manual_mode:
            return

        # Handle things if it is night
        if not self._is_light_out():
            # Turn everything off, it's night time
            for relay in RelayId:
                HardwareState.set_relay(relay, False)
            return  # no more until the morning.

        # Circuit 1 regulation
        if HardwareState.circuits_enabled[0]:  # If circuit is "turned on"
            # Check temperature
            reading = HardwareState.cur_sensor_values[SensorId.t1]
            if reading is None:
                HardwareState.set_relay(RelayId.circ1, False)
            else:
                current_temp = reading.cald
                target_temp = DynConfig.target_temp_tank1_f
                hysteresis = DynConfig.temp_hysteresis
                
                if current_temp < (target_temp - hysteresis):
                    HardwareState.set_relay(RelayId.circ1, True)
                elif current_temp > target_temp:
                    HardwareState.set_relay(RelayId.circ1, False)
        else:
            HardwareState.set_relay(RelayId.circ1, False)

        # Circuit 2 regulation
        if HardwareState.circuits_enabled[1]:  # If circuit is "turned on"
            # Check temperature
            reading = HardwareState.cur_sensor_values[SensorId.t2]
            if reading is None:
                HardwareState.set_relay(RelayId.circ2, False)
            else:
                current_temp = reading.cald
                target_temp = DynConfig.target_temp_tank2_f
                hysteresis = DynConfig.temp_hysteresis
                
                if current_temp < (target_temp - hysteresis):
                    HardwareState.set_relay(RelayId.circ2, True)
                elif current_temp > target_temp:
                    HardwareState.set_relay(RelayId.circ2, False)
        else:
            HardwareState.set_relay(RelayId.circ2, False) 

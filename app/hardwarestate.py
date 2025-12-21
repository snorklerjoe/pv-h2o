""" This holds the overall states / contexts """

from .utils import synchronized
import threading
from loguru import logger
from datetime import datetime
from typing import Optional
from config import Config
from .calibration import SensorReading
from .hardware import sensor_drivers, relay_drivers
from drivers.base_driver import BaseSensorDriver, BaseOutputDriver
from .dynconfig import DynConfig
from .hardware_constants import SensorId, RelayId
from threading import Thread
from time import sleep


class HardwareState:
    """ This class contains the most recent sensor values, the current state of the relays, etc. """
    
    _instance = None
    _instancelock = threading.RLock()
    _pollingthread = None
    _running = True

    cur_sensor_values: dict[SensorId, Optional[SensorReading]] = dict(
        (key, None) for key in SensorId  # Fill with dict of None for each sensor we have
    )
    last_polled: Optional[datetime] = None
    circuits_enabled: Optional[list[bool]] = None

    @staticmethod
    def init():
        """ Initializes the static hardware state """
        HardwareState.circuits_enabled = DynConfig.circuit_states

    @staticmethod
    def poll_sensors():
        """ Polls all hardware inputs, updating current context & saving to the database """
        with HardwareState._instancelock:
            logger.debug("Polling from sensors")

            # poll current sensor values
            new_sensor_values = {}
            for sensor_id in HardwareState.cur_sensor_values.keys():
                driver: BaseSensorDriver = sensor_drivers[sensor_id]
                new_sensor_values[sensor_id] = driver.read()

            # Update the "current" latest values all at once (reference updates are atomic)
            HardwareState.cur_sensor_values = new_sensor_values

            # Update last polled time
            HardwareState.last_polled = datetime.now(Config.TIMEZONE)

    @staticmethod
    def start_sensorpolling():
        """ Starts a thread to continuously poll the sensor data at a rate defined in dynconf """
        with HardwareState._instancelock:
            if HardwareState._pollingthread is not None and HardwareState._pollingthread.is_alive():
                return

            def continuouspoll():
                while HardwareState._running:
                    HardwareState.poll_sensors()
                    sleep(DynConfig.polling_rate_seconds)
            HardwareState._pollingthread = Thread(target=continuouspoll, name="Sensor polling", daemon=True)
            HardwareState._pollingthread.start()

    @staticmethod
    def set_relay(id: RelayId, new_state: bool, force: bool = False) -> None:
        """ Sets the state of the given relay. 
        If the state is already as desired, nothing happens unless force is True.
        """
        with HardwareState._instancelock:
            # Figure out what the appropriate hardware driver is
            driver: BaseOutputDriver = relay_drivers[id]
            
            cur_state: None | bool = driver.get_state()
            if cur_state == new_state and not force:
                return  # We have nothing to do here :)
            
            # Ask the driver to change the state of the relay for us, and block until it's done
            driver.set_state(new_state)

            # Keep track of the change
        HardwareState._relay_states[id] = new_state


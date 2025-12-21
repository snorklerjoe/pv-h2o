""" This holds the overall states / contexts """

from utils import synchronized
import threading
from loguru import logger
from datetime import datetime
from typing import Optional
from config import Config
from calibration import SensorReading
from hardware import SensorId

class Hardware:
    """ Contains all hardware-software interaction code """

class HardwareState:
    """ This class contains the most recent sensor values, the current state of the relays, etc. """
    
    _instance = None
    _instancelock = threading.RLock()

    cur_sensor_values: dict[SensorId, Optional[SensorReading]] = dict(
        (key, None) for key in SensorId  # Fill with dict of None for each sensor we have
    )
    last_polled: Optional[datetime] = None

    @synchronized
    def poll_sensors():
        """ Polls all hardware inputs, updating current context & saving to the database """
        logger.debug("Polling from sensors")


        new_sensor_values = {}

        # Set current sensor values
        for sensor_id in HardwareState.cur_sensor_values.keys:
            new_sensor_values[sensor_id] = 

        HardwareState.cur_sensor_values = new_sensor_values

        # Update last polled time
        last_polled = datetime.now(Config.TIMEZONE)


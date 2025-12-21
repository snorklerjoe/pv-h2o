""" This holds the overall states / contexts """

from utils import synchronized
import threading
from loguru import logger

class Hardware:
    """ Contains all hardware-software interaction code """

class HardwareState:
    """ This class contains the most recent sensor values, the current state of the relays, etc. """
    
    _instance = None
    _instancelock = threading.RLock()

    @synchronized
    def poll_sensors():
        """ Polls all hardware inputs, updating current context & saving to the database """
        logger.debug("Polling from sensors")



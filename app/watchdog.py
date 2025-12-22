""" Watchdog logic for the system """

from abc import ABC, abstractmethod
from enum import Enum
from typing import Type, Optional

from app.dynconfig import DynConfig
from loguru import logger

class WatchdogTrigger(ABC):
    """ Specifies a particular thing to be checking for.
    """
    _all_triggers: list[Type['WatchdogTrigger']] = []
    _alarm_state: bool = False
    _triggered_check: Optional[Type['WatchdogTrigger']] = None

    # Register subclasses
    def __init_subclass__(cls):
        WatchdogTrigger._all_triggers.append(cls)
        cls._alarm_state = False
        return super().__init_subclass__()

    @classmethod
    def all_triggers(cls):
        return WatchdogTrigger._all_triggers
    
    @classmethod
    def trigger_alarm_state(cls):
        # Only trip the master alarm if this trigger is NOT excluded
        if cls.__name__ not in DynConfig.watchdog_excludes:
            if not WatchdogTrigger._alarm_state: # Only log on transition
                 logger.critical(f"Watchdog ALARM triggered by {cls.__name__}")
            
            cls._alarm_state = True
            WatchdogTrigger._alarm_state = True
            WatchdogTrigger._triggered_check = cls
        else:
            logger.warning(f"Watchdog trigger {cls.__name__} met, but excluded from alarm.")

    @staticmethod
    def clear_alarm():
        if WatchdogTrigger._alarm_state:
             logger.info("Clearing all watchdog alarms")
        for trigger in WatchdogTrigger._all_triggers:
            trigger.clear()
        WatchdogTrigger._alarm_state = False
        WatchdogTrigger._triggered_check = None
    
    @staticmethod
    def gen_notify_repr():
        notify_str: str = ""
        if WatchdogTrigger.is_tripped():
            notify_str = f"{WatchdogTrigger._triggered_check.notify_state()}\n\n"
        notify_str += "Summary of watchdog checks:\n"
        for check in WatchdogTrigger.all_triggers():
            notify_str += "  - " + check.notify_state() + "\n"
        return notify_str


    @classmethod
    def is_tripped(cls):
        return cls._alarm_state

    @classmethod
    def check_all(cls):
        """ Run all registered watchdog checks """
        for trigger in cls._all_triggers:
            trigger.run_check()

    @classmethod
    @abstractmethod
    def run_check(cls) -> None:
        """ Check for the condition and trigger alarm if met """
        pass

    @classmethod
    @abstractmethod
    def notify_state(cls) -> str:
        """ Return a string describing the state of this trigger """
        pass

    @classmethod
    def clear(cls) -> None:
        """ Clear any state associated with this trigger """
        cls._alarm_state = False


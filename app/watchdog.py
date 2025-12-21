""" Watchdog logic for the system """

from abc import ABC, abstractmethod
from enum import Enum
from typing import Type, Optional

class WatchdogTrigger(ABC):
    """ Specifies a particular thing to be checking for.
    """
    _all_triggers: list[Type['WatchdogTrigger']] = []
    _alarm_state: bool = False
    _triggered_check: Optional[Type['WatchdogTrigger']] = None

    # Register subclasses
    def __init_subclass__(cls):
        WatchdogTrigger._all_triggers.append(cls)
        return super().__init_subclass__()

    @staticmethod
    @property
    def all_triggers():
        return WatchdogTrigger._all_triggers
    
    @classmethod
    def trigger_alarm_state(cls):
        WatchdogTrigger._alarm_state = True
        WatchdogTrigger._triggered_check = cls

    @staticmethod
    def clear_alarm():
        for trigger in WatchdogTrigger._all_triggers:
            trigger.clear()
        WatchdogTrigger._alarm_state = False
        WatchdogTrigger._triggered_check = None
    
    @staticmethod
    def gen_notify_repr():
        notify_str: str = ""
        if WatchdogTrigger.is_tripped:
            notify_str = f"{WatchdogTrigger._triggered_check.notify_state()}\n\n"
        notify_str += "Summary of watchdog checks:\n"
        for check in WatchdogTrigger.all_triggers:
            notify_str += "  - " + check.notify_state() + "\n"
        return notify_str


    @staticmethod
    @property
    def is_tripped():
        return WatchdogTrigger._alarm_state

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
    @abstractmethod
    def clear(cls) -> None:
        """ Clear any state associated with this trigger """
        pass


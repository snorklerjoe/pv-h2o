""" Status display
Constantly displays status on 20x4 character lcd
"""

from . import hardware
from typing import NoReturn
from threading import Thread
from time import sleep

def splash_screen() -> None:
    """ This is run right after hardware initialization until all systems operational"""
    hardware.lcd_driver.clear()
    hardware.lcd_driver.set_backlight(True)
    hardware.lcd_driver.write_line(1, "PV Hot Water Control")
    hardware.lcd_driver.write_line(2, "  Initializing...   ")

_status_display_thread: Thread | None = None

def _status_display() -> NoReturn:
    """ A forever loop that updates the status lcd with relevant info """
    sleep(5)
    hardware.lcd_driver.clear()
    hardware.lcd_driver.set_backlight(True)
    while True:
        hardware.lcd_driver.clear()  # Status & About
        hardware.lcd_driver.write_line(1, "PV Hot Water Control")
        # TODO: Status
        sleep(5)
        # TODO: Show temperature & voltage
        sleep(5)
        # TODO: Show watchdog state
        sleep(5)

def start_status_display() -> None:
    _status_display_thread = Thread(target=_status_display,name="Status Display", daemon=True)
    _status_display_thread.start()

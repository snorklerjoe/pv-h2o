""" Status display
Constantly displays status on 20x4 character lcd
"""

from . import hardware
from typing import NoReturn
from threading import Thread
from time import sleep
from datetime import datetime
from .hardwarestate import HardwareState
from .hardware_constants import SensorId, RelayId
from .regulation import Regulator
from .watchdog import WatchdogTrigger
from .dynconfig import DynConfig
from app.config import Config
from loguru import logger

def splash_screen() -> None:
    """ This is run right after hardware initialization until all systems operational"""
    if not hardware.lcd_driver: return
    hardware.lcd_driver.clear()
    hardware.lcd_driver.set_backlight(True)
    hardware.lcd_driver.write_line(1, "PV Hot Water Control")
    hardware.lcd_driver.write_line(2, "  Initializing...   ")

_status_display_thread: Thread | None = None

def _status_display() -> NoReturn:
    """ A forever loop that updates the status lcd with relevant info """
    sleep(5)
    if not hardware.lcd_driver:
        return

    hardware.lcd_driver.set_backlight(False)
    
    while True:
        try:
            # --- Screen 1: Overview ---
            hardware.lcd_driver.clear()
            
            # Line 0: Title & Time
            now = datetime.now(Config.TIMEZONE)
            time_str = now.strftime("%H:%M")
            hardware.lcd_driver.write_line(0, f"PV-H2O Sys    {time_str}")
            
            # Line 1: Regulator Mode & Light
            mode = "Man" if DynConfig.manual_mode else "Auto"
            light = "Day" if Regulator()._is_light_out() else "Night"
            hardware.lcd_driver.write_line(1, f"Mode:{mode:<3}  Env:{light}")

            # Line 2: Circuit States
            c1_state = "ON" if HardwareState.get_relay_state(RelayId.circ1) else "OFF"
            c2_state = "ON" if HardwareState.get_relay_state(RelayId.circ2) else "OFF"
            hardware.lcd_driver.write_line(2, f"C1:{c1_state:<3}      C2:{c2_state:<3}")

            # Line 3: Safety Status
            wd_status = "TRIP" if WatchdogTrigger.is_tripped() else "OK"
            
            # Check GFCI status
            gfci_tripped = False
            if hardware.gfci_driver:
                t1 = hardware.gfci_driver.is_tripped(1)
                t2 = hardware.gfci_driver.is_tripped(2)
                gfci_tripped = t1 or t2
            
            gf_status = "TRIP" if gfci_tripped else "OK"
            hardware.lcd_driver.write_line(3, f"WD:{wd_status:<4}     GF:{gf_status:<4}")
            
            sleep(DynConfig.lcd_status_period)

            # --- Screen 2: Circuit 1 ---
            hardware.lcd_driver.clear()
            hardware.lcd_driver.write_line(0, "Circuit 1 (Tank 1)")
            
            t1_val = HardwareState.cur_sensor_values[SensorId.t1]
            t1_str = f"{t1_val.cald:.1f}" if t1_val else "--.-"
            
            v1_val = HardwareState.cur_sensor_values[SensorId.v1]
            v1_str = f"{v1_val.cald:.1f}" if v1_val else "--.-"
            
            i1_val = HardwareState.cur_sensor_values[SensorId.i1]
            i1_str = f"{i1_val.cald:.1f}" if i1_val else "--.-"
            
            p1_str = "----"
            if v1_val and i1_val:
                p1_str = f"{v1_val.cald * i1_val.cald:.0f}"

            hardware.lcd_driver.write_line(1, f"Temp: {t1_str} F")
            hardware.lcd_driver.write_line(2, f"Pwr : {p1_str} W")
            hardware.lcd_driver.write_line(3, f"{v1_str}V       {i1_str}A")
            
            sleep(DynConfig.lcd_status_period)

            # --- Screen 3: Circuit 2 ---
            hardware.lcd_driver.clear()
            hardware.lcd_driver.write_line(0, "Circuit 2 (Tank 2)")
            
            t2_val = HardwareState.cur_sensor_values[SensorId.t2]
            t2_str = f"{t2_val.cald:.1f}" if t2_val else "--.-"
            
            v2_val = HardwareState.cur_sensor_values[SensorId.v2]
            v2_str = f"{v2_val.cald:.1f}" if v2_val else "--.-"
            
            i2_val = HardwareState.cur_sensor_values[SensorId.i2]
            i2_str = f"{i2_val.cald:.1f}" if i2_val else "--.-"
            
            p2_str = "----"
            if v2_val and i2_val:
                p2_str = f"{v2_val.cald * i2_val.cald:.0f}"

            hardware.lcd_driver.write_line(1, f"Temp: {t2_str} F")
            hardware.lcd_driver.write_line(2, f"Pwr : {p2_str} W")
            hardware.lcd_driver.write_line(3, f"{v2_str}V       {i2_str}A")
            
            sleep(DynConfig.lcd_status_period)
            
            # --- Screen 4: Environment ---
            hardware.lcd_driver.clear()
            hardware.lcd_driver.write_line(0, "Environment")
            
            t0_val = HardwareState.cur_sensor_values[SensorId.t0]
            t0_str = f"{t0_val.cald:.1f}" if t0_val else "--.-"
            hardware.lcd_driver.write_line(1, f"Water In: {t0_str} F")
            
            if WatchdogTrigger.is_tripped():
                 hardware.lcd_driver.write_line(2, "!! WATCHDOG TRIP !!")
                 hardware.lcd_driver.write_line(3, "CHECK DASHBOARD")
            elif gfci_tripped:
                 hardware.lcd_driver.write_line(2, "!! GFCI TRIPPED !!")
                 hardware.lcd_driver.write_line(3, "CHECK DASHBOARD")
            else:
                 hardware.lcd_driver.write_line(2, "System Nominal")
            
            sleep(DynConfig.lcd_status_period)

        except Exception as e:
            logger.exception("Issue with status display")
            try:
                hardware.lcd_driver.clear()
                hardware.lcd_driver.write_line(0, "Display Error")
                hardware.lcd_driver.write_line(1, str(e)[:20])
            except:
                logger.exception("Issue connecting to the LCD")
            sleep(DynConfig.lcd_status_period)

def start_status_display() -> None:
    _status_display_thread = Thread(target=_status_display,name="Status Display", daemon=True)
    _status_display_thread.start()

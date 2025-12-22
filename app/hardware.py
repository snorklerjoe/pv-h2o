""" Code for accessing hardware """

from drivers.base_driver import BaseSensorDriver, BaseOutputDriver, BaseLCDDriver, BaseGFCIDriver, HardwareDriver
from drivers.dummy_driver import DummySensorDriver, DummyOutputDriver, DummyLCDDriver, DummyGFCIDriver
from typing import Type
from app.dynconfig import DynConfig, MalformedConfigException
from app.hardware_constants import SensorId, RelayId
from loguru import logger
from typing import Type
import sys

drivers_initialized = False
hardware_initialized = False

sensor_drivers = {}
relay_drivers = {}
lcd_driver = None
gfci_driver = None

def get_all_drivers() -> dict[str,HardwareDriver]:
    return {'lcd': lcd_driver, **sensor_drivers, **relay_drivers}

def initialize_drivers():
    """ Reads drivers and driver configuration from DynConf.
    Initialized driver instances are then found in the dictionaries in this module.
    """
    global drivers_initialized, lcd_driver, gfci_driver
    if drivers_initialized:  # Re-init of drivers...
        drivers_initialized = False  # de-validate drivers

    # Check if dynamic conf is configured yet
    if not DynConfig.initialized:
        logger.error("Dynamic config not initialized -- CANNOT initialize drivers.")
        raise ValueError("Dynamic config not initialized!")

    # get conf -- should be a dictionary of {key: tuple (driver name, dict of params)}
    try:
        sensor_driver_conf = DynConfig.driver_sensors
        output_driver_conf = DynConfig.driver_relays
        lcd_driver_conf = DynConfig.driver_lcd
        gfci_driver_conf = DynConfig.driver_gfci
    except MalformedConfigException:  # Malformed config goes through eval()
        logger.opt(exception=True).error(f"Malformed driver config. Cannot initialize drivers.")
        raise

    # Do sensors
    for sensor in SensorId:
        try:
            DriverClass: Type[BaseSensorDriver] = BaseSensorDriver.get_driver(
                sensor_driver_conf[sensor.value][0]
            )
            sensor_drivers[sensor] = DriverClass(sensor_driver_conf[sensor.value][1])
        except KeyError as e:  # We don't have a sensor driver config specified for this sensor
            logger.warning(f"No driver found for sensor {sensor.name}... Using dummy driver.")
            logger.opt(exception=True).debug("(A KeyError exception occurred)")
            sensor_drivers[sensor] = DummySensorDriver({})  # No parameters (use defaults)     

    # Do Relays
    for relay in RelayId:
        try:
            DriverClass: Type[BaseOutputDriver] = BaseOutputDriver.get_driver(
                output_driver_conf[relay.value][0]
            )
            relay_drivers[relay] = DriverClass(output_driver_conf[relay.value][1])
        except KeyError:  # We don't have a sensor driver config specified for this sensor
            logger.warning(f"No driver found for output {relay.name}... Using dummy driver.")
            logger.opt(exception=True).debug("(A KeyError exception occurred)")
            relay_drivers[relay] = DummyOutputDriver({})  # No parameters (use defaults)     

    # Do LCD
    try:
        DriverClass: Type[BaseLCDDriver] = BaseLCDDriver.get_driver(
            lcd_driver_conf[0]
        )
        lcd_driver = DriverClass(lcd_driver_conf[1])
    except KeyError:  # We don't have a sensor driver config specified for this sensor
        logger.warning(f"No driver found for lcd... Using dummy driver.")
        logger.opt(exception=True).debug("(A KeyError exception occurred)")
        lcd_driver = DummyLCDDriver({})  # No parameters (use defaults)   

    # Do GFCI  
    try:
        DriverClass: Type[BaseGFCIDriver] = BaseGFCIDriver.get_driver(
            gfci_driver_conf[0]
        )
        gfci_driver = DriverClass(gfci_driver_conf[1])
    except KeyError:  # We don't have a sensor driver config specified for this sensor
        logger.warning(f"No driver found for GFCI... Using dummy driver.")
        logger.opt(exception=True).debug("(A KeyError exception occurred)")
        gfci_driver = DummyGFCIDriver({})  # No parameters (use defaults)   

    drivers_initialized = True

def initialize_hardware():
    """ Runs the init method of each hardware driver
    Must be run after drivers are initialized """
    global hardware_initialized
    if not drivers_initialized:
        raise ValueError("Drivers are not initialized. Cannot initialize hardware.")
    if hardware_initialized:  # If hardware is already brought up, bring it down first
        logger.warning("Force-deinitializing hardware before re-initializing it.")
        deinitialize_hardware()
    for name, driver in get_all_drivers().items():
        logger.debug(f"Intializing {name}.")
        driver.hardware_init()
    hardware_initialized = True

def deinitialize_hardware(force: bool = False):
    """ Runs the init method of each hardware driver
    Must be run after drivers are initialized """
    global hardware_initialized
    if not drivers_initialized:
        raise ValueError("Drivers are not initialized. Cannot deinitialize hardware.")
    if not force and not hardware_initialized:
        raise ValueError("Hardware has not been initialized. Cannot deinitialize hardware.")
    for name, driver in get_all_drivers().items():
        logger.debug(f"Deinitializing {name}.")
        driver.hardware_deinit()
    hardware_initialized = False

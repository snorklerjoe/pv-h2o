""" Code for accessing hardware """

from drivers.base_driver import BaseSensorDriver, BaseOutputDriver, BaseLCDDriver
from drivers.dummy_driver import DummySensorDriver, DummyOutputDriver, DummyLCDDriver
from typing import Type
from app.dynconfig import DynConfig, MalformedConfigException
from app.constants import SensorId, RelayId
from loguru import logger

drivers_initialized = False
sensor_drivers = {}
relay_drivers = {}
lcd_driver = None

def initialize_drivers():
    """ Reads drivers and driver configuration from DynConf.
    Initialized driver instances are then found in the dictionaries in this module.
    """
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
    except MalformedConfigException:  # Malformed config goes through eval()
        logger.error(f"Malformed driver config. Cannot initialize drivers.")
        raise

    # Do sensors
    for sensor in SensorId:
        try:
            DriverClass: Class[BaseSensorDriver] = BaseSensorDriver.get_driver(
                sensor_driver_conf[sensor][0]
            )
            sensor_drivers[sensor] = DriverClass(sensor_driver_conf[sensor][1])
        except KeyError:  # We don't have a sensor driver config specified for this sensor
            logger.warning(f"No driver found for sensor {sensor.name}... Using dummy driver.")
            sensor_drivers[sensor] = DummySensorDriver({})  # No parameters (use defaults)     

    # Do Relays
    for relay in RelayId:
        try:
            DriverClass: Class[BaseOutputDriver] = BaseOutputDriver.get_driver(
                output_driver_conf[relay][0]
            )
            relay_drivers[relay] = DriverClass(output_driver_conf[sensor][1])
        except KeyError:  # We don't have a sensor driver config specified for this sensor
            logger.warning(f"No driver found for output {relay.name}... Using dummy driver.")
            relay_drivers[relay] = DummyOutputDriver({})  # No parameters (use defaults)     

    # Do LCD
    try:
        DriverClass: Class[BaseLCDDriver] = BaseLCDDriver.get_driver(
            lcd_driver_conf[0]
        )
        lcd_driver = DriverClass(lcd_driver_conf[1])
    except KeyError:  # We don't have a sensor driver config specified for this sensor
        logger.warning(f"No driver found for lcd... Using dummy driver.")
        lcd_driver = DummyLCDDriver({})  # No parameters (use defaults)     

    drivers_initialized = True



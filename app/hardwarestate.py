""" This holds the overall states / contexts """

from .utils import synchronized
import threading
from loguru import logger
from datetime import datetime
from typing import Optional
from app.config import Config
from .calibration import SensorReading
from .hardware import sensor_drivers, relay_drivers, gfci_driver
from drivers.base_driver import BaseSensorDriver, BaseOutputDriver, GFCIRelay
from .dynconfig import DynConfig
from .hardware_constants import SensorId, RelayId
from threading import Thread
from time import sleep
from app import db
from app.models import Measurement


class HardwareState:
    """ This class contains the most recent sensor values, the current state of the relays, etc. """
    
    _instance = None
    _instancelock = threading.RLock()

    cur_sensor_values: dict[SensorId, Optional[SensorReading]] = dict(
        (key, None) for key in SensorId  # Fill with dict of None for each sensor we have
    )
    _relay_states: dict[RelayId, bool] = dict(
        (key, False) for key in RelayId
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
                new_sensor_values[sensor_id] = SensorReading(driver.read(), sensor_id)

            # Update relay states for GFCIRelay drivers
            for relay_id, driver in relay_drivers.items():
                if isinstance(driver, GFCIRelay):
                    HardwareState._relay_states[relay_id] = driver.get_state()

            # Update the "current" latest values all at once (reference updates are atomic)
            HardwareState.cur_sensor_values = new_sensor_values

            # Update last polled time
            HardwareState.last_polled = datetime.now(Config.TIMEZONE)

            # Save to database
            try:
                m = Measurement(
                    timestamp=HardwareState.last_polled,
                    # Raw
                    v1_raw=new_sensor_values[SensorId.v1].raw if new_sensor_values[SensorId.v1] else None,
                    i1_raw=new_sensor_values[SensorId.i1].raw if new_sensor_values[SensorId.i1] else None,
                    t1_raw=new_sensor_values[SensorId.t1].raw if new_sensor_values[SensorId.t1] else None,
                    v2_raw=new_sensor_values[SensorId.v2].raw if new_sensor_values[SensorId.v2] else None,
                    i2_raw=new_sensor_values[SensorId.i2].raw if new_sensor_values[SensorId.i2] else None,
                    t2_raw=new_sensor_values[SensorId.t2].raw if new_sensor_values[SensorId.t2] else None,
                    t0_raw=new_sensor_values[SensorId.t0].raw if new_sensor_values[SensorId.t0] else None,
                    # Calibrated
                    v1_cal=new_sensor_values[SensorId.v1].cald if new_sensor_values[SensorId.v1] else None,
                    i1_cal=new_sensor_values[SensorId.i1].cald if new_sensor_values[SensorId.i1] else None,
                    t1_cal=new_sensor_values[SensorId.t1].cald if new_sensor_values[SensorId.t1] else None,
                    v2_cal=new_sensor_values[SensorId.v2].cald if new_sensor_values[SensorId.v2] else None,
                    i2_cal=new_sensor_values[SensorId.i2].cald if new_sensor_values[SensorId.i2] else None,
                    t2_cal=new_sensor_values[SensorId.t2].cald if new_sensor_values[SensorId.t2] else None,
                    t0_cal=new_sensor_values[SensorId.t0].cald if new_sensor_values[SensorId.t0] else None,
                    # Relays
                    relay_inside_1=HardwareState.get_relay_state(RelayId.circ1),
                    relay_inside_2=HardwareState.get_relay_state(RelayId.circ2),
                    relay_outside_1=HardwareState.get_relay_state(RelayId.gfci1),
                    relay_outside_2=HardwareState.get_relay_state(RelayId.gfci2)
                )
                db.session.add(m)
                db.session.commit()
            except Exception as e:
                logger.error(f"Error saving measurement to DB: {e}")
                db.session.rollback()

    @staticmethod
    def schedule_sensor_polling(flask_app):
        """ Schedules the sensor polling job """
        from app import scheduler
        from app.utils import run_with_timeout_and_kill
        
        def job():
            def task():
                with flask_app.app_context():
                    HardwareState.poll_sensors()

            run_with_timeout_and_kill(
                task, 
                timeout=DynConfig.polling_rate_seconds
            )

        if scheduler.get_job('sensor_polling'):
            scheduler.remove_job('sensor_polling')

        scheduler.add_job(
            id='sensor_polling',
            func=job,
            trigger='interval',
            seconds=DynConfig.polling_rate_seconds,
            max_instances=1,
            coalesce=True
        )

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
            
            logger.info(f"Relay {id.name} changed state: {cur_state} -> {new_state}")

            # Keep track of the change
            HardwareState._relay_states[id] = new_state

    @staticmethod
    def get_relay_state(id: RelayId) -> bool:
        return HardwareState._relay_states.get(id, False)

    @staticmethod
    def sync_gfci_settings():
        """ Syncs the GFCI settings from DynConfig to the hardware driver """
        if gfci_driver:
            logger.info("Syncing GFCI settings to hardware...")
            gfci_driver.set_threshold(DynConfig.gfci_trip_threshold_ma)
            gfci_driver.set_tolerance(DynConfig.gfci_response_factor)
            gfci_driver.set_enabled(DynConfig.gfci_enabled)


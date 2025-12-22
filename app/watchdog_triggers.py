""" Watchdog triggers implementation """

from app.watchdog import WatchdogTrigger
from app.hardwarestate import HardwareState
from app.hardware_constants import SensorId, RelayId
from app.dynconfig import DynConfig
from app.models import SystemConfig
from app import db
from loguru import logger

def disable_circuit(circuit_idx):
    try:
        # We need to ensure we are working with the latest config
        current_states = list(DynConfig.circuit_states)
        if current_states[circuit_idx]:
            current_states[circuit_idx] = False
            
            # We need to be inside an app context to access the DB if we aren't already
            # The scheduler usually provides one, but let's be safe? 
            # Actually, we can't easily get the app instance here without circular imports or passing it down.
            # However, db.session might work if the thread has context.
            
            conf = SystemConfig.query.filter_by(key='circuit_states').first()
            if conf:
                conf.value = str(current_states)
                db.session.commit()
                DynConfig.reload()
                logger.warning(f"Watchdog disabled circuit {circuit_idx+1} due to fault.")
    except Exception as e:
        logger.error(f"Failed to disable circuit {circuit_idx}: {e}")

class OverCurrentTrigger(WatchdogTrigger):
    @classmethod
    def run_check(cls) -> None:
        limit = DynConfig.trip_current_max_amps
        
        # Check Circuit 1
        reading = HardwareState.cur_sensor_values[SensorId.i1]
        if reading:
            i1 = reading.cald
            if i1 > limit:
                cls.trigger_alarm_state()
                HardwareState.set_relay(RelayId.circ1, False)
                disable_circuit(0)
            
        # Check Circuit 2
        reading = HardwareState.cur_sensor_values[SensorId.i2]
        if reading:
            i2 = reading.cald
            if i2 > limit:
                cls.trigger_alarm_state()
                HardwareState.set_relay(RelayId.circ2, False)
                disable_circuit(1)

    @classmethod
    def notify_state(cls) -> str:
        if cls.is_tripped():
            return f"Over Current Trigger: Limit {DynConfig.trip_current_max_amps}A exceeded."
        return f"Over Current Trigger: Limit {DynConfig.trip_current_max_amps}A met."

class OverTemperatureTrigger(WatchdogTrigger):
    @classmethod
    def run_check(cls) -> None:
        limit = DynConfig.trip_temp_max_f
        
        # Check Tank 1
        reading = HardwareState.cur_sensor_values[SensorId.t1]
        if reading:
            t1 = reading.cald
            if t1 > limit:
                cls.trigger_alarm_state()
                HardwareState.set_relay(RelayId.circ1, False)
                disable_circuit(0)
            
        # Check Tank 2
        reading = HardwareState.cur_sensor_values[SensorId.t2]
        if reading:
            t2 = reading.cald
            if t2 > limit:
                cls.trigger_alarm_state()
                HardwareState.set_relay(RelayId.circ2, False)
                disable_circuit(1)

    @classmethod
    def notify_state(cls) -> str:
        if cls.is_tripped():
            return f"Over Temperature Trigger: Limit {DynConfig.trip_temp_max_f}F exceeded."
        return f"Over Temperature Trigger: Limit {DynConfig.trip_temp_max_f}F met."

class SubnominalResistanceTrigger(WatchdogTrigger):
    @classmethod
    def run_check(cls) -> None:
        min_ohms = DynConfig.trip_impedance_min_ohms
        
        # Check Circuit 1
        r_v1 = HardwareState.cur_sensor_values[SensorId.v1]
        r_i1 = HardwareState.cur_sensor_values[SensorId.i1]
        if r_v1 and r_i1:
            v1 = r_v1.cald
            i1 = r_i1.cald
            if i1 > 1.0: # Only check if significant current is flowing
                r1 = v1 / i1
                if r1 < min_ohms:
                    cls.trigger_alarm_state()
                    HardwareState.set_relay(RelayId.circ1, False)
                    disable_circuit(0)

        # Check Circuit 2
        r_v2 = HardwareState.cur_sensor_values[SensorId.v2]
        r_i2 = HardwareState.cur_sensor_values[SensorId.i2]
        if r_v2 and r_i2:
            v2 = r_v2.cald
            i2 = r_i2.cald
            if i2 > 1.0:
                r2 = v2 / i2
                if r2 < min_ohms:
                    cls.trigger_alarm_state()
                    HardwareState.set_relay(RelayId.circ2, False)
                    disable_circuit(1)

    @classmethod
    def notify_state(cls) -> str:
        if cls.is_tripped():
            return f"Sub-nominal Resistance Trigger: Resistance above {DynConfig.trip_impedance_min_ohms} Ohms."
        return f"Sub-nominal Resistance Trigger: Resistance below {DynConfig.trip_impedance_min_ohms} Ohms."

class LeakageCurrentTrigger(WatchdogTrigger):
    @classmethod
    def run_check(cls) -> None:
        threshold = DynConfig.trip_leakage_threshold_amps
        
        # Check Circuit 1
        if not HardwareState.get_relay_state(RelayId.circ1):
            reading = HardwareState.cur_sensor_values[SensorId.i1]
            if reading:
                i1 = reading.cald
                if i1 > threshold:
                    cls.trigger_alarm_state()
                    HardwareState.set_relay(RelayId.circ1, False)
                    disable_circuit(0)

        # Check Circuit 2
        if not HardwareState.get_relay_state(RelayId.circ2):
            reading = HardwareState.cur_sensor_values[SensorId.i2]
            if reading:
                i2 = reading.cald
                if i2 > threshold:
                    cls.trigger_alarm_state()
                    HardwareState.set_relay(RelayId.circ2, False)
                    disable_circuit(1)

    @classmethod
    def notify_state(cls) -> str:
        if cls.is_tripped():
            return f"Leakage Current Trigger: Current measurement stays below {DynConfig.trip_leakage_threshold_amps}A while relay OFF."
        return f"Leakage Current Trigger: Current > {DynConfig.trip_leakage_threshold_amps}A detected while relay OFF."

""" Watchdog triggers implementation """

from watchdog import WatchdogTrigger
from hardwarestate import HardwareState
from hardware_constants import SensorId, RelayId
from dynconfig import DynConfig

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
            
        # Check Circuit 2
        reading = HardwareState.cur_sensor_values[SensorId.i2]
        if reading:
            i2 = reading.cald
            if i2 > limit:
                cls.trigger_alarm_state()
                HardwareState.set_relay(RelayId.circ2, False)

    @classmethod
    def notify_state(cls) -> str:
        return f"Over Current Trigger: Limit {DynConfig.trip_current_max_amps}A exceeded."

    @classmethod
    def clear(cls) -> str:
        pass

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
            
        # Check Tank 2
        reading = HardwareState.cur_sensor_values[SensorId.t2]
        if reading:
            t2 = reading.cald
            if t2 > limit:
                cls.trigger_alarm_state()
                HardwareState.set_relay(RelayId.circ2, False)

    @classmethod
    def notify_state(cls) -> str:
        return f"Over Temperature Trigger: Limit {DynConfig.trip_temp_max_f}F exceeded."

    @classmethod
    def clear(cls) -> str:
        pass

class ImpedanceMismatchTrigger(WatchdogTrigger):
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

    @classmethod
    def notify_state(cls) -> str:
        return f"Impedance Mismatch Trigger: Resistance below {DynConfig.trip_impedance_min_ohms} Ohms."

    @classmethod
    def clear(cls) -> str:
        pass

class LeakageCurrentTrigger(WatchdogTrigger):
    @classmethod
    def run_check(cls) -> None:
        threshold = DynConfig.trip_leakage_threshold_amps
        
        # Check Circuit 1
        if not HardwareState.get_relay(RelayId.circ1):
            reading = HardwareState.cur_sensor_values[SensorId.i1]
            if reading:
                i1 = reading.cald
                if i1 > threshold:
                    cls.trigger_alarm_state()
                    HardwareState.set_relay(RelayId.circ1, False)

        # Check Circuit 2
        if not HardwareState.get_relay(RelayId.circ2):
            reading = HardwareState.cur_sensor_values[SensorId.i2]
            if reading:
                i2 = reading.cald
                if i2 > threshold:
                    cls.trigger_alarm_state()
                    HardwareState.set_relay(RelayId.circ2, False)

    @classmethod
    def notify_state(cls) -> str:
        return f"Leakage Current Trigger: Current > {DynConfig.trip_leakage_threshold_amps}A detected while relay OFF."

    @classmethod
    def clear(cls) -> str:
        pass

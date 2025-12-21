""" This module handles calibration tables and actually calculating the calibrated values.
"""

from app.models import CalibrationPoint
from functools import cached_property
from typing import Dict, List, Optional
from app.constants import SensorId

class CalibrationRegistry:
    """
    Singleton-like registry that holds cached calibration tables.
    """
    _cache: Dict[SensorId, List[CalibrationPoint]] = {}

    @classmethod
    def get_points(cls, sensor: SensorId) -> List[CalibrationPoint]:
        """
        Returns cached points. If not in cache, fetches from DB.
        """
        if sensor not in cls._cache:
            # print(f"Cache miss for {sensor.name}, fetching from DB...")
            cls._cache[sensor] = CalibrationPoint.query\
                .filter_by(sensor_id=sensor.value)\
                .order_by(CalibrationPoint.measured_val)\
                .all()
        return cls._cache[sensor]

    @classmethod
    def invalidate(cls, sensor: Optional[SensorId] = None):
        """
        Clears the cache. Call this when the user updates calibration settings.
        """
        if sensor:
            if sensor in cls._cache:
                del cls._cache[sensor]
        else:
            cls._cache.clear()

class CalTable:
    """
    Defines a table of calibration values.
    """
    def __init__(self, sensor: SensorId):
        self.sensor = sensor

    @property
    def points(self) -> List[CalibrationPoint]:
        return CalibrationRegistry.get_points(self.sensor)

    def apply_cal(self, value: float) -> float:
        """ Runs the given value through the interpolated cal table """
        points = self.points

        # If there aren't even enough points to form a single line, don't bother
        # with the calibration at all:
        if len(points) < 2:
            return value

        # Otherwise, find the two nearest points that bound this point:
        # Perform a binary search (it's already ordered) to find the two
        # datapoints that bound `value`
        left, right = 0, len(points) - 1
        while right - left > 1:
            mid = (left + right) // 2
            if points[mid].measured_val < value:
                left = mid
            else:
                right = mid
        lower_point = points[left]
        upper_point = points[right]

        # Now, interpolate along a straight line between `lower_point` and
        # `upper_point`.
        denom = (upper_point.measured_val - lower_point.measured_val)
        if denom == 0:  # Avoid division by zero
            # (theoretically very unlikely to have multiple points within
            # float precision, but just to be safe)
            return lower_point.actual_val
            
        slope = (upper_point.actual_val - lower_point.actual_val) / denom
        return slope * (value - lower_point.measured_val) + lower_point.actual_val


class SensorReading:
    """
    A raw value and a cal'd value, based on a calibration table
    """
    def __init__(self, measured_val: float, sensor_id: SensorId):
        self.meas = measured_val
        self.sensor_id = sensor_id

    @cached_property
    def cald(self) -> float:
        """ The calibrated value """
        return CalibrationRegistry.get_points(self.sensor_id).apply_cal(self.meas)

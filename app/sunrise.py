""" Handles getting sunrise and sunset """

from astral import LocationInfo
from astral.sun import sun
from datetime import datetime, timedelta
from app.config import Config
from app.dynconfig import DynConfig

def get_sun_rise_set_time_today() -> tuple[datetime, datetime]:
    """ Returns a tuple of (sunrise time, sunset time) """
    tz = Config.TIMEZONE_NAME.split('/')
    loc = LocationInfo(DynConfig.location_name,
                       tz[0], Config.TIMEZONE_NAME,
                       DynConfig.location_lat,
                       DynConfig.location_long)
    s = sun(loc.observer, date=datetime.now(Config.TIMEZONE), tzinfo=loc.timezone)
    return (s['sunrise'], s['sunset'])

def light_window() -> tuple[datetime, datetime]:
    """ Returns the window based on the DynConfig """
    sunrise, sunset = get_sun_rise_set_time_today()
    rise_delta = timedelta(minutes=DynConfig.sunrise_offset_minutes)
    set_delta = timedelta(minutes=DynConfig.sunset_offset_minutes)
    return (sunrise + rise_delta, sunset - set_delta)
    # return (sunset - set_delta, sunrise + rise_delta)


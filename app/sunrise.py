""" Handles getting sunrise and sunset """

from astral import LocationInfo
from astral.sun import sun
import datetime

from config import Config
from app.dynconfig import DynConfig

def get_sun_rise_set_time_today() -> tuple[datetime.datetime, datetime.datetime]:
    """ Returns a tuple of (sunrise time, sunset time) """
    tz = Config.TIMEZONE_NAME.split('/')
    loc = LocationInfo(DynConfig.location_name,
                       tz[0], Config.TIMEZONE_NAME,
                       DynConfig.location_lat,
                       DynConfig.location_long)
    s = sun(loc.observer, date=datetime.datetime.today(), tzinfo=loc.timezone)
    return (s['sunrise'], s['sunset'])

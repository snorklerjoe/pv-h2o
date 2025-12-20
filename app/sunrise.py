""" Handles getting sunrise and sunset """

from astral import LocationInfo, sun
import datetime

from config import Config
from dynconfig import DynConfig

def get_sun_rise_set_time_today() -> datetime.datetime:
    tz = Config.TIMEZONE_NAME.split('/')
    loc = LocationInfo(DynConfig.location_name,
                       tz[0], Config.TIMEZONE_NAME,
                       DynConfig.location_lat,
                       DynConfig.location_long)
    s = sun(loc.observer, date=datetime.datetime.today(), tzinfo=loc.timezone)
    return (s['sunrise'], s['sunset'])

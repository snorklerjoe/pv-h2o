import pytest
import datetime
from unittest.mock import patch, MagicMock
from app.sunrise import get_sun_rise_set_time_today
from app.config import Config

# Mock Config and DynConfig
@pytest.fixture
def mock_config():
    with patch('app.sunrise.Config') as MockConfig:
        MockConfig.TIMEZONE_NAME = 'America/New_York'
        yield MockConfig

@pytest.fixture
def mock_dynconfig():
    with patch('app.sunrise.DynConfig') as MockDynConfig:
        MockDynConfig.location_name = 'TestCity'
        MockDynConfig.location_lat = 40.7128
        MockDynConfig.location_long = -74.0060
        yield MockDynConfig

def test_get_sun_rise_set_time_today(mock_config, mock_dynconfig):
    # We can't easily predict the exact sunrise/sunset without reimplementing the logic,
    # but we can check that it returns two datetime objects and sunrise is before sunset.
    
    sunrise, sunset = get_sun_rise_set_time_today()
    
    assert isinstance(sunrise, datetime.datetime)
    assert isinstance(sunset, datetime.datetime)
    assert sunrise < sunset
    
    # Check that the date is today
    today = datetime.datetime.today().date()
    assert sunrise.date() == today
    assert sunset.date() == today

def test_get_sun_rise_set_time_today_different_location(mock_config, mock_dynconfig):
    # Change location to somewhere significantly different (e.g. London)
    mock_config.TIMEZONE_NAME = 'Europe/London'
    mock_dynconfig.location_lat = 51.5074
    mock_dynconfig.location_long = -0.1278
    
    sunrise, sunset = get_sun_rise_set_time_today()
    
    assert isinstance(sunrise, datetime.datetime)
    assert isinstance(sunset, datetime.datetime)
    assert sunrise < sunset

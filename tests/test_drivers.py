import pytest
from drivers.dummy_driver import DummySensorDriver, DummyOutputDriver, DummyLCDDriver

def test_sensor_driver():
    driver = DummySensorDriver({'value': 50.0, 'noise': 0.0})
    assert driver.read() == 50.0
    
    driver_noise = DummySensorDriver({'value': 50.0, 'noise': 1.0})
    val = driver_noise.read()
    assert 49.0 <= val <= 51.0

def test_output_driver():
    driver = DummyOutputDriver()
    assert not driver.get_state()
    driver.set_state(True)
    assert driver.get_state()

def test_lcd_driver():
    driver = DummyLCDDriver()
    # Just ensure methods don't crash
    driver.write_line(0, "Hello")
    driver.clear()
    driver.set_backlight(True)

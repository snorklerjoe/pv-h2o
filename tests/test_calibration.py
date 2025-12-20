import pytest
from app import create_app, db
from app.models import CalibrationPoint, SensorId
from app.calibration import CalibrationRegistry, CalTable
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        # Clear cache before each test
        CalibrationRegistry.invalidate()
        yield app
        db.session.remove()
        db.drop_all()

def test_calibration_interpolation(app):
    # Add points: (0,0), (10, 100)
    p1 = CalibrationPoint(sensor_id=SensorId.v1.value, measured_val=0.0, actual_val=0.0)
    p2 = CalibrationPoint(sensor_id=SensorId.v1.value, measured_val=10.0, actual_val=100.0)
    db.session.add_all([p1, p2])
    db.session.commit()

    ct = CalTable(SensorId.v1)
    
    # Test interpolation
    assert abs(ct.apply_cal(5.0) - 50.0) < 1e-6
    assert abs(ct.apply_cal(0.0) - 0.0) < 1e-6
    assert abs(ct.apply_cal(10.0) - 100.0) < 1e-6
    
    # Test extrapolation (linear)
    assert abs(ct.apply_cal(15.0) - 150.0) < 1e-6

def test_registry_caching(app):
    p1 = CalibrationPoint(sensor_id=SensorId.v1.value, measured_val=0.0, actual_val=0.0)
    p2 = CalibrationPoint(sensor_id=SensorId.v1.value, measured_val=10.0, actual_val=10.0)
    db.session.add_all([p1, p2])
    db.session.commit()

    # First fetch hits DB
    points1 = CalibrationRegistry.get_points(SensorId.v1)
    assert len(points1) == 2

    # Add another point directly to DB
    p3 = CalibrationPoint(sensor_id=SensorId.v1.value, measured_val=20.0, actual_val=20.0)
    db.session.add(p3)
    db.session.commit()

    # Second fetch should hit cache (still 2 points)
    points2 = CalibrationRegistry.get_points(SensorId.v1)
    assert len(points2) == 2

    # Invalidate
    CalibrationRegistry.invalidate(SensorId.v1)
    
    # Third fetch hits DB (now 3 points)
    points3 = CalibrationRegistry.get_points(SensorId.v1)
    assert len(points3) == 3

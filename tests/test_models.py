import pytest
from app import create_app, db
from app.models import User, Measurement
from app.constants import SensorId
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_user_password(app):
    u = User(username='test')
    u.set_password('pass')
    assert u.check_password('pass')
    assert not u.check_password('wrong')

def test_measurement_creation(app):
    m = Measurement(v1_raw=120.0, relay_inside_1=True)
    db.session.add(m)
    db.session.commit()
    assert Measurement.query.count() == 1
    assert Measurement.query.first().v1_raw == 120.0

import pytest
from app import create_app, db
import app as app_module
from app.models import User, Measurement
from app.config import Config
from datetime import datetime, timedelta
import json

@pytest.fixture
def client():
    # Reset global state to ensure initialize_backend runs if needed, 
    # or at least doesn't block if we want it to.
    # Actually, for testing, we might NOT want initialize_backend to run fully 
    # (e.g. hardware init), but create_app calls it.
    # We can mock it or just let it run.
    # But we must ensure DB is clean.
    
    app = create_app(Config)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.drop_all() # Ensure clean slate
            db.create_all()
            
            # Create user
            u = User(username='test')
            u.set_password('test')
            db.session.add(u)
            
            # Create some measurements
            base_time = datetime.now(Config.TIMEZONE)
            for i in range(10):
                m = Measurement(
                    timestamp=base_time + timedelta(minutes=i),
                    v1_cal=120.0 + i,
                    i1_cal=5.0 + i/10.0,
                    relay_inside_1=True
                )
                db.session.add(m)
            db.session.commit()
            
        yield client
        
        with app.app_context():
            db.session.remove()
            db.drop_all()

def login(client, username, password):
    return client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)

def test_get_history_simple(client):
    login(client, 'test', 'test')
    response = client.get('/api/history')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['timestamps']) == 10
    assert 'v1' in data['sensors']

def test_get_history_derived(client):
    login(client, 'test', 'test')
    derived = [{"name": "p1", "expr": "v1 * i1"}]
    response = client.get(f'/api/history?derived_defs={json.dumps(derived)}&sensors=v1,p1')
    assert response.status_code == 200
    data = response.get_json()
    assert 'p1' in data['sensors']
    # Check calculation: (120+0) * (5+0) = 600
    assert data['sensors']['p1'][0] == 600.0

def test_get_history_downsample(client):
    login(client, 'test', 'test')
    response = client.get('/api/history?downsample_factor=2')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['timestamps']) == 5 # 10 / 2

def test_get_history_integrate(client):
    login(client, 'test', 'test')
    # e1 = integrate(v1) -> cumsum of v1
    derived = [{"name": "e1", "expr": "integrate(v1)"}]
    response = client.get(f'/api/history?derived_defs={json.dumps(derived)}&sensors=e1')
    assert response.status_code == 200
    data = response.get_json()
    assert 'e1' in data['sensors']
    vals = data['sensors']['e1']
    assert vals[0] == 120.0
    assert vals[1] == 120.0 + 121.0


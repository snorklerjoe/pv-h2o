from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from enum import Enum
from app.config import Config

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    name = db.Column(db.String(64))
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now(Config.TIMEZONE))
    
    # Raw Sensor Values
    v1_raw = db.Column(db.Float)
    i1_raw = db.Column(db.Float)
    t1_raw = db.Column(db.Float)
    v2_raw = db.Column(db.Float)
    i2_raw = db.Column(db.Float)
    t2_raw = db.Column(db.Float)
    t0_raw = db.Column(db.Float)
    
    # Calibrated Values
    v1_cal = db.Column(db.Float)
    i1_cal = db.Column(db.Float)
    t1_cal = db.Column(db.Float)
    v2_cal = db.Column(db.Float)
    i2_cal = db.Column(db.Float)
    t2_cal = db.Column(db.Float)
    t0_cal = db.Column(db.Float)
    
    # Circuit States (Booleans or Integers representing state)
    relay_inside_1 = db.Column(db.Boolean)
    relay_inside_2 = db.Column(db.Boolean)

    relay_outside_1 = db.Column(db.Boolean)
    relay_outside_2 = db.Column(db.Boolean)

class CalibrationPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.String(64), index=True) # e.g., 'v1', 't2'
    measured_val = db.Column(db.Float)
    actual_val = db.Column(db.Float)

class DailySummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, index=True, unique=True)
    kwh_total = db.Column(db.Float)
    peak_watts = db.Column(db.Float)
    max_temp_1 = db.Column(db.Float)
    min_temp_1 = db.Column(db.Float)
    max_temp_2 = db.Column(db.Float)
    min_temp_2 = db.Column(db.Float)

class SystemConfig(db.Model):
    """Key-value store for dynamic system settings"""
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.String(256))

class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now(Config.TIMEZONE))
    level = db.Column(db.String(20))
    message = db.Column(db.String(512))
    module = db.Column(db.String(64))


import os
from zoneinfo import ZoneInfo

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    
    # Database configuration
    # Use SQLite by default for development, but allow override for MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    TIMEZONE_NAME = "America/New_York"
    TIMEZONE = ZoneInfo("America/New_York")

    WATCDOG_PERIOD_SEC = 90

    SUMMARY_RUN_HOUR = 22

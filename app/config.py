import os
from zoneinfo import ZoneInfo
import git

try:
    _this_git_repo = git.Repo(search_parent_directories=True)
    _commit_sha = _this_git_repo.head.object.hexsha
except Exception:
    _commit_sha = "unknown"

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    
    # Paths
    # Allow overriding paths for database and logs (e.g. for external storage)
    DB_FILE_PATH = os.environ.get('DB_FILE_PATH') or os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    LOG_FILE_PATH = os.environ.get('LOG_FILE_PATH') or os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.log')

    # Database configuration
    # Use SQLite by default for development, but allow override for MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + DB_FILE_PATH
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    TIMEZONE_NAME = "America/New_York"
    TIMEZONE = ZoneInfo("America/New_York")

    WATCDOG_PERIOD_SEC = 90

    SUMMARY_RUN_HOUR = 22

    COMMIT_SHA = _commit_sha

    REAL_HARDWARE = os.environ.get('REAL_HARDWARE', 'False').lower() in ('true', '1', 't')

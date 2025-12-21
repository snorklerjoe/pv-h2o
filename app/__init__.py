import sys
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from loguru import logger

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'login'

# Import these after db is defined to avoid circular imports
from .dynconfig import DynConfig, MalformedConfigException

def initialize_backend():
    # Fetch dynamic configuration from the database
    DynConfig.fetch_config()
    if not DynConfig.initialized:
        logger.critical("Cannot fetch config from database. Aborting.")
        sys.exit(1)
    
    # Initialize & configure hardware drivers
    from app.hardware import initialize_drivers
    try:
        initialize_drivers()
    except ValueError:
        logger.critical("Cannot initialize hardware drivers. Aborting.")
        sys.exit(1)
    except MalformedConfigException:
        logger.critical("Malformed driver configuration; cannot initialize hardware. Aborting.")
        sys.exit(1)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login.init_app(app)

    from app import routes, models
    
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app

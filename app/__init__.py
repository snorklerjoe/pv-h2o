""" Main PV-H2O Control Webapp

Backend stuff, web app stuff, and hardware interface stuff are combined.
Thus, it is very important that whatever wsgi server is used only spins up a SINGLE WORKER.

Multiple threads are okay, but this can only handle a single worker.

Future modification might move all hardware stuff to a separate daemon and make the webserver stateless.
For now, it seems that would be an unnecessary level of overcomplication.

"""

import sys
import signal
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_apscheduler import APScheduler
from loguru import logger
import traceback

# Configure logger
logger.add("app.log", rotation="1 MB", retention="10 days", colorize=True)

db = SQLAlchemy()
scheduler = APScheduler()
login = LoginManager()
login.login_view = 'login'
_backend_initialized = False

from .dynconfig import DynConfig, MalformedConfigException
from .notification import NotificationService
notifier = NotificationService()

from .stats import run_summary
from .statusdisplay import splash_screen, start_status_display

# Import these after db is defined to avoid circular imports
from .dynconfig import DynConfig, MalformedConfigException

def shutdown_handler(signum, frame):
    logger.info(f"Received signal {signum}. Shutting down...")
    from app.hardware import deinitialize_hardware
    try:
        deinitialize_hardware(force=True)
        logger.info("Hardware de-initialized successfully.")
    except Exception as e:
        logger.error(f"Error de-initializing hardware: {e}")
    sys.exit(0)

def initialize_backend(flask_app):
    # Register signal handlers
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    db.create_all()
    # Create default user if none exists
    from app.models import User
    try:
        if User.query.first() is None:
            logger.info("No users found. Creating default admin user.")
            u = User(username='admin')
            u.set_password('1234')
            db.session.add(u)
            db.session.commit()
    except Exception as e:
        logger.error(f"Error checking/creating default user: {e}")

    # Fetch dynamic configuration from the database
    DynConfig.fetch_config()
    if not DynConfig.initialized:
        logger.critical("Cannot fetch config from database. Aborting.")
        sys.exit(1)
    
    # Initialize & configure hardware drivers
    from app.hardware import initialize_drivers, initialize_hardware, deinitialize_hardware
    try:
        initialize_drivers()
    except ValueError:
        logger.critical("Cannot initialize hardware drivers. Aborting.")
        sys.exit(1)
    except MalformedConfigException:
        logger.critical("Malformed driver configuration; cannot initialize hardware. Aborting.")
        sys.exit(1)

    # Bring up the hardware
    try:
        initialize_hardware()
    except Exception as e:
        logger.critical("Error while initializing hardware. Attempting to safely deinit...")
        try: 
            deinitialize_hardware(force=True)
            logger.info("Successfully de-initialized hardware.")
        except:
            logger.critical("Could not de-initialize hardware.")
        traceback.print_exc()
        sys.exit(1)
    
    # Show LCD splash screen now that hardware is initialized
    splash_screen()

    # Initialize the notifier
    notifier.init()

    # Set up the watchdog timer
    from .watchdog import WatchdogTrigger
    import app.watchdog_triggers # Register triggers
    @scheduler.task('interval', id='watchdog', seconds=Config.WATCDOG_PERIOD_SEC, misfire_grace_time=3*Config.WATCDOG_PERIOD_SEC)
    def watchdog():
        was_not_tripped: bool = not WatchdogTrigger.is_tripped()
        any_tripped: bool = False
        for check in list(WatchdogTrigger.all_triggers()):
            check.run_check()
            any_tripped = any_tripped or check.is_tripped()
        if not any_tripped and not was_not_tripped:  # Make sure clearing propagates back up to master alarm state
            WatchdogTrigger.clear()

        if was_not_tripped and WatchdogTrigger.is_tripped() and DynConfig.notify_email_enabled:  # Send a notification if something just happened
            notifier.send_alert(
                "Solar Watchdog Tripped",
                WatchdogTrigger.gen_notify_repr()
            )

    # Schedule saving daily summary stats to database
    @scheduler.task('cron', id='summary', minute=0, hour=str(Config.SUMMARY_RUN_HOUR))
    def summary():
        run_summary()
    
    if not scheduler.running:
        scheduler.start()

    # Get the sensor polling loop going
    from .hardwarestate import HardwareState
    HardwareState.start_sensorpolling(flask_app)

    # Get the regulation loop going
    from .regulation import Regulator
    regulator = Regulator()
    regulator.start_regulation(flask_app)

    # Begin a thread to handle the status LCD display loop
    start_status_display()



def create_app(config_class=Config):
    logger.info(f"Photovoltaic hot water control software (code commit version {Config.COMMIT_SHA})")
    logger.info("Starting...")

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login.init_app(app)
    
    from apscheduler.schedulers import SchedulerAlreadyRunningError
    try:
        scheduler.init_app(app)
    except SchedulerAlreadyRunningError:
        logger.warning("Scheduler already running. Cannot initialize with app context.")

    # Set up backend stuff
    global _backend_initialized   # Ensure we only initialize things ONCE
    if not _backend_initialized:
        # We must push an app context so that initialize_backend can access the DB
        with app.app_context():
            # Check if we are in a "Werkzeug reloader" child process or a Gunicorn worker
            # This prevents double-init if you ever run with 'flask run' in debug mode
            import os
            if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
                logger.info("Performing backend initialization...")
                initialize_backend(app)
                _backend_initialized = True
            else:
                logger.info("Skipping backend init (Main process of debug reloader)")


    # Set up webapp stuff

    from app import routes, models
    
    logger.debug("Registering blueprints")
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    logger.info("Web app initialized.")
    return app

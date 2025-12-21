""" Main PV-H2O Control Webapp

Backend stuff, web app stuff, and hardware interface stuff are combined.
Thus, it is very important that whatever wsgi server is used only spins up a SINGLE WORKER.

Multiple threads are okay, but this can only handle a single worker.

Future modification might move all hardware stuff to a separate daemon and make the webserver stateless.
For now, it seems that would be an unnecessary level of overcomplication.

"""

import sys
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_apscheduler import APScheduler
from loguru import logger
import traceback
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

def initialize_backend():
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
    @scheduler.task('interval', id='watchdog', seconds=Config.WATCDOG_PERIOD_SEC, misfire_grace_time=3*Config.WATCDOG_PERIOD_SEC)
    def watchdog():
        was_not_tripped: bool = not WatchdogTrigger.is_tripped
        for check in WatchdogTrigger.all_triggers:
            check.run_check()
        if was_not_tripped and WatchdogTrigger.is_tripped and DynConfig.notify_email_enabled():  # Send a notification if something just happened
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
    HardwareState.start_sensorpolling()

    # Get the regulation loop going
    from .regulation import Regulator
    Regulator.start_regulation()

    # Begin a thread to handle the status LCD display loop
    start_status_display()



def create_app(config_class=Config):
    logger.info("Initializing web application")
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login.init_app(app)
    
    from apscheduler.schedulers import SchedulerAlreadyRunningError
    try:
        scheduler.init_app(app)
    except SchedulerAlreadyRunningError:
        pass

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
                initialize_backend()
                _backend_initialized = True
            else:
                logger.info("Skipping backend init (Main process of debug reloader)")


    # Set up webapp stuff

    from app import routes, models
    
    logger.debug("Registering blueprints")
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    logger.info("Web app initialized.")
    return app

from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login.init_app(app)

    from app import routes, models
    
    # Register routes directly for now, or use blueprints if it gets larger
    # For simplicity in this initial setup, we'll import routes to register them
    # with the app instance if we were using the single-module pattern, 
    # but with the factory pattern, we usually use blueprints.
    # Let's stick to a simple app context push for now or define routes in routes.py 
    # taking app as argument, or better yet, use a Blueprint.
    
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app

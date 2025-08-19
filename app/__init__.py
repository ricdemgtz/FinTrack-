from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from .config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Import models so Alembic can see them
    from . import models  # noqa: F401

    # Register blueprints
    from .auth.routes import auth_bp
    from .api.routes import api_bp
    from .web.routes import web_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(web_bp)

    # Create DB tables on first run (SQLite dev convenience)
    with app.app_context():
        db.create_all()

    return app

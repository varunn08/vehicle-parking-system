import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(os.path.dirname(basedir), 'instance', 'slotly.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_secret_key_here'

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'user_bp.login'

    # Register Blueprints
    from .routes.user_routes import user_bp
    from .routes.admin_routes import admin_bp
    from .routes.main_routes import main_bp

    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)

    return app

from .models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

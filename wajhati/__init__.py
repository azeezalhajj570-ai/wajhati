import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

from config import Config
from wajhati.translations import tr_category, tr_city, tr_description, tr_destination, tr_interest_tag, tr_season

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    app.jinja_env.globals.update(
        tr_city=tr_city,
        tr_description=tr_description,
        tr_destination=tr_destination,
        tr_interest_tag=tr_interest_tag,
        tr_category=tr_category,
        tr_season=tr_season,
    )

    from wajhati.routes.auth import auth_bp
    from wajhati.routes.main import main_bp
    from wajhati.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        from wajhati.seed import seed_default_users, seed_demo_destinations

        db.create_all()
        _ensure_user_profile_columns()
        _ensure_destination_columns()
        seed_default_users()
        _ensure_admin_user()
        seed_demo_destinations()

    return app


def _ensure_user_profile_columns():
    inspector = inspect(db.engine)
    columns = {column["name"] for column in inspector.get_columns("user")}
    statements = []
    if "age_range" not in columns:
        statements.append("ALTER TABLE user ADD COLUMN age_range VARCHAR(40)")
    if "gender" not in columns:
        statements.append("ALTER TABLE user ADD COLUMN gender VARCHAR(40)")
    if "favorite_tags" not in columns:
        statements.append("ALTER TABLE user ADD COLUMN favorite_tags VARCHAR(255) NOT NULL DEFAULT ''")
    if "is_admin" not in columns:
        statements.append("ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()


def _ensure_destination_columns():
    inspector = inspect(db.engine)
    columns = {column["name"] for column in inspector.get_columns("destination")}
    statements = []
    if "image_url" not in columns:
        statements.append("ALTER TABLE destination ADD COLUMN image_url VARCHAR(500)")

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()


def _ensure_admin_user():
    from wajhati.models import User

    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    updated = False

    if admin_email:
        admin_user = User.query.filter_by(email=admin_email).first()
        if admin_user and not admin_user.is_admin:
            admin_user.is_admin = True
            updated = True

    if User.query.count() and User.query.filter_by(is_admin=True).count() == 0:
        first_user = User.query.order_by(User.id.asc()).first()
        if first_user and not first_user.is_admin:
            first_user.is_admin = True
            updated = True

    if updated:
        db.session.commit()

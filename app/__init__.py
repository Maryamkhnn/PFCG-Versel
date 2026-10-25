from flask import Flask
from flask_mail import Mail
from datetime import timedelta

from app.config import Config
from app.database import db

mail = Mail()


def create_app():

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
    app.config.from_object(Config)

    db.init_app(app)
    mail.init_app(app)

    # Main blueprints
    from app.auth import auth
    from app.admin import admin
    from app.user.routes import user

    # Notification blueprint
    from app.user.notification_routes import notifications

    app.register_blueprint(auth)
    app.register_blueprint(admin, url_prefix="/admin")
    app.register_blueprint(user, url_prefix="/user")

    # Notification blueprint already includes /user prefix
    app.register_blueprint(notifications)

    # SEO title and meta description suggestions
    from app.user.controllers.seo_controller import (
        seo_suggest_metadata_api
    )

    app.add_url_rule(
        "/user/api/seo-suggest-metadata",
        endpoint="seo_suggest_metadata_api",
        view_func=seo_suggest_metadata_api,
        methods=["POST"]
    )

    return app
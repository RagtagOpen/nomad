import logging
from flask import Flask, g, render_template
from flask_bootstrap import Bootstrap
from flask_caching import Cache
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from .config import config

bootstrap = Bootstrap()
mail = Mail()
db = SQLAlchemy()
migrate = Migrate()
cache = Cache()

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    logger = app.logger
    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler()
    logger.addHandler(stream_handler)

    bootstrap.init_app(app)
    mail.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    if app.config.get('SSLIFY_ENABLE'):
        app.logger.info("Using SSLify")
        from flask_sslify import SSLify
        sslify = SSLify(app)

    sentry = None
    if app.config.get('SENTRY_ENABLE'):
        app.logger.info("Using Sentry")
        from raven.contrib.flask import Sentry
        sentry = Sentry(app)

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template(
            '500.html',
            event_id=g.sentry_event_id,
            public_dsn=sentry.client.get_public_dsn('https') if sentry else None
        )

    @app.after_request
    def frame_buster(response):
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.after_request
    def server_header(response):
        response.headers['Server'] = 'Server'
        return response

    from .carpool import pool_bp
    app.register_blueprint(pool_bp)

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .admin import admin_bp
    app.register_blueprint(admin_bp)

    return app

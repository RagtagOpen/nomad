from flask import (
    Flask,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    url_for
)
from flask_bootstrap import Bootstrap
from flask_caching import Cache
from flask_login import LoginManager, logout_user, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from raven.contrib.flask import Sentry
from .config import config

csrf = CSRFProtect()
bootstrap = Bootstrap()
mail = Mail()
db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
sentry = Sentry()

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    csrf.init_app(app)
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
        sentry = Sentry(app)

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template(
            '500.html',
            event_id=g.sentry_event_id,
            public_dsn=sentry.client.get_public_dsn('https') if sentry else None
        )

    @app.errorhandler(400)
    def error_400(error):
        return render_template(
            '400.html'
        )

    @app.errorhandler(403)
    def error_403(error):
        return render_template(
            '403.html'
        )

    @app.errorhandler(404)
    def error_404(error):
        return render_template(
            '404.html'
        )

    @app.after_request
    def frame_buster(response):
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.after_request
    def server_header(response):
        response.headers['Server'] = 'Server'
        return response

    @app.template_filter('humanize')
    def humanize(dt):
        return dt.strftime(app.config.get('DATE_FORMAT'))

    from .carpool import pool_bp
    app.register_blueprint(pool_bp)

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .admin import admin_bp
    app.register_blueprint(admin_bp)

    @app.before_request
    def block_handling():
        """ Log out a user that's blocked and send them to the index page. """
        if not current_user.is_anonymous and current_user.has_roles('blocked'):
            flash("There was a problem with your login.", 'error')
            current_app.logger.warn("Logged out blocked user %s",
                                    current_user.id)
            logout_user()
            return redirect(url_for('auth.login'))

    return app

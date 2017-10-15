import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', None)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://localhost/carpools')
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    DEBUG = os.environ.get('FLASK_DEBUG', False)
    VERBOSE_SQLALCHEMY = False
    SSLIFY_ENABLE = False
    SENTRY_ENABLE = False
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')
    INTERCOM_KEY = os.environ.get('INTERCOM_KEY')
    GOOGLE_ANALYTICS_ID = os.environ.get('GOOGLE_ANALYTICS_ID')

    # SERVER_NAME is needed here so the email worker can
    # know what to put in while generating URLs.
    SERVER_NAME = os.environ.get('SERVER_NAME')
    RQ_ENABLED = os.environ.get('RQ_ENABLED', False)
    RQ_REDIS_URL = os.environ.get('REDIS_URL')
    MAIL_LOG_ONLY = os.environ.get('MAIL_LOG_ONLY', True)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = os.environ.get('MAIL_PORT', 25)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', False)
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', False)
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'from@example.com')
    PREFERRED_URL_SCHEME = 'https'

    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_PROTECTION = 'strong'

    TRIP_MAX_LENGTH_DAYS = 21
    TRIP_MAX_DAYS_IN_FUTURE = 90

    OAUTH_CREDENTIALS = {
        'facebook': {
            'id': os.environ.get('FACEBOOK_CLIENT_ID'),
            'secret': os.environ.get('FACEBOOK_CLIENT_SECRET'),
        },
        'google': {
            'id': os.environ.get('GOOGLE_CLIENT_ID'),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
        },
    }

    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    DATE_FORMAT = os.environ.get('DATE_FORMAT', '%a %b %-d %Y at %-I:%M %p')

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))
    DEBUG = os.environ.get('FLASK_DEBUG', True)

    # Set this environment variable if you're using
    # Ngrok for local testing
    ENABLE_PROXYFIX = os.environ.get('ENABLE_PROXYFIX')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        if app.config.get('ENABLE_PROXYFIX'):
            # handle proxy server headers
            from werkzeug.contrib.fixers import ProxyFix
            app.wsgi_app = ProxyFix(app.wsgi_app)

        if app.config.get('VERBOSE_SQLALCHEMY'):
            import logging
            from logging import StreamHandler
            stream_handler = StreamHandler()
            stream_handler.setLevel(logging.INFO)
            sql_logger = logging.getLogger('sqlalchemy.engine')
            sql_logger.addHandler(stream_handler)
            sql_logger.setLevel(logging.INFO)


class TestingConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/circle_test'
    TESTING = True


class HerokuConfig(Config):
    SSLIFY_ENABLE = True
    SENTRY_ENABLE = True

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # handle proxy server headers
        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

        # log to stderr
        import logging
        from logging import StreamHandler
        stream_handler = StreamHandler()
        stream_handler.setLevel(logging.WARNING)
        app.logger.addHandler(stream_handler)


class StagingConfig(HerokuConfig):
    DEBUG = False
    TESTING = False


class ProductionConfig(HerokuConfig):
    DEBUG = False
    TESTING = False


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}

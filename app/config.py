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

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = os.environ.get('MAIL_PORT', 25)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'from@example.com')
    PREFERRED_URL_SCHEME = 'https'

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

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))
    DEBUG = os.environ.get('FLASK_DEBUG', True)
    PREFERRED_URL_SCHEME = 'http'

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

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
    SSL_DISABLE = bool(os.environ.get('SSL_DISABLE'))

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


class ProductionConfig(HerokuConfig):
    DEBUG = False
    TESTING = False
    SSLIFY_ENABLE = True
    SENTRY_ENABLE = True


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}

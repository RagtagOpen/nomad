from flask import abort
from flask_login import current_user
from functools import wraps


def requires_roles(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.has_roles(roles) not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return wrapper

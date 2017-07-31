from flask import abort
from flask_login import current_user
from functools import wraps


def roles_required(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.has_roles(roles):
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return wrapper

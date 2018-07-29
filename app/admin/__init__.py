from flask import Blueprint
from flask_login import fresh_login_required
from ..auth.permissions import roles_required

admin_bp = Blueprint('admin', __name__)

# This ensures that all admin_bp routes require a fresh login with admin permissions
@admin_bp.before_request
@fresh_login_required
@roles_required('admin')
def before_request():
    pass


from . import views

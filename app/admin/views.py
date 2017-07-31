from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import login_required
from . import admin_bp
from ..auth.permissions import roles_required


@admin_bp.route('/admin/')
@login_required
@roles_required('admin')
def admin_index():
    return 'you are admin'

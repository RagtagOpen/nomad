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
from ..models import Person


@admin_bp.route('/admin/')
@login_required
@roles_required('admin')
def admin_index():
    return render_template(
        'admin/index.html',
    )


@admin_bp.route('/admin/users/<int:user_id>')
@login_required
@roles_required('admin')
def user_show(user_id):
    user = Person.query.get_or_404(user_id)
    return render_template(
        'admin/show_user.html',
        user=user,
    )


@admin_bp.route('/admin/users')
@login_required
@roles_required('admin')
def user_list():
    page = request.args.get('page')
    page = int(page) if page is not None else None
    per_page = 15

    users = Person.query.\
        order_by(Person.created_at.desc()).\
        paginate(page, per_page)

    return render_template(
        'admin/users_list.html',
        users=users,
    )


@admin_bp.route('/admin/destinations')
@login_required
@roles_required('admin')
def destinations_list():
    return render_template(
        'admin/destinations_list.html',
    )

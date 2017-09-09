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
from .. import db
from ..auth.permissions import roles_required
from ..models import Destination, Person, Role, PersonRole


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


@admin_bp.route('/admin/users/<int:user_id>/role/<role_name>/toggle')
@login_required
@roles_required('admin')
def user_toggle_role(user_id, role_name):
    user = Person.query.get_or_404(user_id)
    role = Role.query.filter_by(name=role_name).first_or_404()

    pr = PersonRole.query.filter_by(person_id=user.id, role_id=role.id).first()
    if pr:
        db.session.delete(pr)
        flash('Role {} removed from this user'.format(role.name))
    else:
        user.roles.append(role)
        flash('Role {} added to this user'.format(role.name))
    db.session.commit()

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
    page = request.args.get('page')
    page = int(page) if page is not None else None
    per_page = 15

    destinations = Destination.query.\
        order_by(Destination.created_at.desc()).\
        paginate(page, per_page)

    return render_template(
        'admin/destinations_list.html',
        destinations=destinations,
    )

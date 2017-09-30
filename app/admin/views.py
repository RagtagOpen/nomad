from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from . import admin_bp
from .forms import DeleteDestinationForm, DestinationForm, EditDeleteDestinationForm, ProfilePurgeForm
from flask_login import current_user, login_required
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from . import admin_bp
from .. import db
from ..auth.permissions import roles_required
from ..carpool.views import (
    cancel_carpool,
    email_driver_rider_cancelled_request,
)
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
        'admin/users/show.html',
        user=user,
    )


@admin_bp.route('/admin/users/<int:user_id>/purge', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def user_purge(user_id):
    user = Person.query.get_or_404(user_id)

    form = ProfilePurgeForm()
    if form.validate_on_submit():
        if form.submit.data:

            if user.id == current_user.id:
                flash("You can't purge yourself", 'error')
                current_app.logger.info("User %s tried to purge themselves",
                                        current_user.id)
                return redirect(url_for('admin.user_show', user_id=user.id))

            if user.has_roles('admin'):
                flash("You can't purge other admins", 'error')
                current_app.logger.info("User %s tried to purge admin %s",
                                        current_user.id, user.id)
                return redirect(url_for('admin.user_show', user_id=user.id))

            try:
                # Delete the ride requests for this user
                for req in user.get_ride_requests_query():
                    current_app.logger.info("Deleting user %s's request %s",
                                            user.id, req.id)
                    email_driver_rider_cancelled_request(req, req.carpool,
                                                         user)
                    db.session.delete(req)

                # Delete the carpools for this user
                for pool in user.get_driving_carpools():
                    current_app.logger.info("Deleting user %s's pool %s",
                                            user.id, pool.id)
                    cancel_carpool(pool)
                    db.session.delete(pool)

                # Delete the user's account
                current_app.logger.info("Deleting user %s", user.id)
                db.session.delete(user)
                db.session.commit()
            except:
                db.session.rollback()
                current_app.logger.exception("Problem deleting user account")
                flash("There was a problem purging the user", 'error')
                return redirect(url_for('admin.user_show', user_id=user.id))

            flash("You deleted the user from the database", 'success')
            return redirect(url_for('admin.user_list'))
        else:
            return redirect(url_for('admin.user_show', user_id=user.id))

    return render_template(
        'admin/users/purge.html',
        user=user,
        form=form,
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

    return redirect(url_for('admin.user_show', user_id=user.id))


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
        'admin/users/list.html',
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
        'admin/destinations/list.html',
        destinations=destinations,
    )


@admin_bp.route('/admin/destinations/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def destinations_add():
    dest_form = DestinationForm()
    if dest_form.validate_on_submit():
        destination = Destination(
            name=dest_form.name.data,
            address=dest_form.address.data,
            point='SRID=4326;POINT({} {})'.format(
                dest_form.destination_lon.data,
                dest_form.destination_lat.data),
        )
        db.session.add(destination)
        db.session.commit()

        flash("You added a destination.", 'success')

        return redirect(
            url_for('admin.destinations_list')
        )

    return render_template(
        'admin/destinations/add.html',
        form=dest_form,
    )


@admin_bp.route('/admin/destinations/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def destinations_show(id):
    dest = Destination.query.get_or_404(id)

    point = to_shape(dest.point)
    edit_form = EditDeleteDestinationForm(name=dest.name, address=dest.address,
                                         destination_lat = point.y,
                                          destination_lon = point.x)


    if edit_form.validate_on_submit():
        if edit_form.submit.data:
            dest.name=edit_form.name.data,
            dest.address=edit_form.address.data,
            dest.point='SRID=4326;POINT({} {})'.format(
                edit_form.destination_lon.data,
                edit_form.destination_lat.data),
            db.session.commit()
            flash("Your destination was updated", 'success')
        elif edit_form.delete.data:
            # TODO Check to make sure no one is using the destination?
            return redirect(url_for('admin.destinations_delete', id=id))
            db.session.delete(dest)
            db.session.commit()
            flash("Your destination was deleted", 'success')
        return redirect(url_for('admin.destinations_list'))
        #return redirect(url_for('admin.destinations_show', id=id))

    return render_template(
        'admin/destinations/edit.html',
        form=edit_form,
    )


@admin_bp.route('/admin/destinations/<int:id>/delete', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def destinations_delete(id):
    dest = Destination.query.get_or_404(id)

    delete_form = DeleteDestinationForm()
    if delete_form.validate_on_submit():
        if delete_form.submit.data:
            # TODO Check to make sure no one is using the destination?
            db.session.delete(dest)
            db.session.commit()

            flash("Your destination was deleted", 'success')
            return redirect(url_for('admin.destinations_list'))
        else:
            return redirect(url_for('admin.destinations_show', id=id))

    return render_template(
        'admin/destinations/delete.html',
        destination=dest,
        form=delete_form,
    )

@admin_bp.route('/admin/destinations/<int:id>/hide')
@login_required
@roles_required('admin')
def destinations_hide(id):
    dest = Destination.query.get_or_404(id)

    dest.hidden = True
    db.session.add(dest)
    db.session.commit()

    flash("Your destination was hidden", 'success')
    return redirect(url_for('admin.destinations_show', id=id))


@admin_bp.route('/admin/destinations/<int:id>/unhide')
@login_required
@roles_required('admin')
def destinations_unhide(id):
    dest = Destination.query.get_or_404(id)

    dest.hidden = False
    db.session.add(dest)
    db.session.commit()

    flash("Your destination was unhidden", 'success')
    return redirect(url_for('admin.destinations_show', id=id))

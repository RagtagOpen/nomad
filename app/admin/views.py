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
from .forms import (
    DeleteDestinationForm,
    DestinationForm,
    ProfilePurgeForm,
)
from geoalchemy2.shape import to_shape
from .. import db
from ..email import (
    send_emails,
    catch_and_log_email_exceptions,
    make_email_message,
)
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


@admin_bp.route('/admin/users/<uuid>')
@login_required
@roles_required('admin')
def user_show(uuid):
    user = Person.uuid_or_404(uuid)
    return render_template(
        'admin/users/show.html',
        user=user,
    )


@admin_bp.route('/admin/users/<uuid>/purge', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def user_purge(uuid):
    user = Person.uuid_or_404(uuid)

    form = ProfilePurgeForm()
    if form.validate_on_submit():
        if form.submit.data:

            if user.id == current_user.id:
                flash("You can't purge yourself", 'error')
                current_app.logger.info("User %s tried to purge themselves",
                                        current_user.id)
                return redirect(url_for('admin.user_show', uuid=user.uuid))

            if user.has_roles('admin'):
                flash("You can't purge other admins", 'error')
                current_app.logger.info("User %s tried to purge admin %s",
                                        current_user.id, user.id)
                return redirect(url_for('admin.user_show', uuid=user.uuid))

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
                return redirect(url_for('admin.user_show', uuid=user.uuid))

            flash("You deleted the user from the database", 'success')
            return redirect(url_for('admin.user_list'))
        else:
            return redirect(url_for('admin.user_show', uuid=user.uuid))

    return render_template(
        'admin/users/purge.html',
        user=user,
        form=form,
    )


@admin_bp.route('/admin/users/<user_uuid>/role/<role_name>/toggle')
@login_required
@roles_required('admin')
def user_toggle_role(user_uuid, role_name):
    user = Person.uuid_or_404(user_uuid)
    role = Role.query.filter_by(name=role_name).first_or_404()

    pr = PersonRole.query.filter_by(person_id=user.id, role_id=role.id).first()
    if pr:
        db.session.delete(pr)
        flash('Role {} removed from this user'.format(role.name))
    else:
        user.roles.append(role)
        flash('Role {} added to this user'.format(role.name))
    db.session.commit()

    return redirect(url_for('admin.user_show', uuid=user.uuid))


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


@admin_bp.route('/admin/destinations/<uuid>', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def destinations_show(uuid):
    dest = Destination.uuid_or_404(uuid)

    point = to_shape(dest.point)
    edit_form = DestinationForm(
        name=dest.name,
        address=dest.address,
        destination_lat=point.y,
        destination_lon=point.x,
    )

    if edit_form.validate_on_submit():
        dest.name = edit_form.name.data
        dest.address = edit_form.address.data
        dest.point = 'SRID=4326;POINT({} {})'.format(
            edit_form.destination_lon.data,
            edit_form.destination_lat.data
        )

        for carpool in dest.carpools:
            carpool.to_place = dest.address
            carpool.to_point = dest.point

        _email_destination_action(dest, 'modified', 'modified')

        db.session.commit()
        flash("Your destination was updated", 'success')
        return redirect(url_for('admin.destinations_show', uuid=uuid))

    return render_template(
        'admin/destinations/edit.html',
        form=edit_form,
        dest=dest,
    )


@admin_bp.route('/admin/destinations/<uuid>/delete', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def destinations_delete(uuid):
    dest = Destination.uuid_or_404(uuid)

    delete_form = DeleteDestinationForm()
    if delete_form.validate_on_submit():
        if delete_form.submit.data:
            _email_destination_action(dest, 'cancelled', 'deleted')
            db.session.delete(dest)
            db.session.commit()

            flash("Your destination was deleted", 'success')
            return redirect(url_for('admin.destinations_list'))
        else:
            return redirect(url_for('admin.destinations_show', uuid=uuid))

    return render_template(
        'admin/destinations/delete.html',
        dest=dest,
        form=delete_form,
    )


def _make_destination_action_email_messages(destination, verb, template_base):
    messages_to_send = []
    for carpool in destination.carpools:
        subject = 'Carpool on {} {}'.format(carpool.leave_time, verb)
        people = [
            ride_request.person for ride_request in carpool.ride_requests
        ]
        people.append(carpool.driver)
        for person in people:
            messages_to_send.append(
                make_email_message(
                    'admin/destinations/email/{}.html'.format(template_base),
                    'admin/destinations/email/{}.txt'.format(template_base),
                    person.email,
                    subject,
                    destination=destination,
                    carpool=carpool,
                    person=person))

    return messages_to_send


def _email_destination_action(dest, verb, template_base):
    messages_to_send = _make_destination_action_email_messages(
        dest, verb, template_base)
    with catch_and_log_email_exceptions(messages_to_send):
        send_emails(messages_to_send)


@admin_bp.route('/admin/destinations/<uuid>/hide')
@login_required
@roles_required('admin')
def destinations_hide(uuid):
    dest = Destination.uuid_or_404(uuid)

    dest.hidden = True
    db.session.add(dest)
    db.session.commit()

    flash("Your destination was hidden", 'success')
    return redirect(url_for('admin.destinations_show', uuid=uuid))


@admin_bp.route('/admin/destinations/<uuid>/unhide')
@login_required
@roles_required('admin')
def destinations_unhide(uuid):
    dest = Destination.uuid_or_404(uuid)

    dest.hidden = False
    db.session.add(dest)
    db.session.commit()

    flash("Your destination was unhidden", 'success')
    return redirect(url_for('admin.destinations_show', uuid=uuid))

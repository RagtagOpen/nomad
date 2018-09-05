import csv
import io
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    Response,
    url_for,
)
from flask_login import current_user
from . import admin_bp
from .forms import (
    CancelCarpoolAdminForm,
    DeleteDestinationForm,
    DestinationForm,
    ProfilePurgeForm,
)
from geoalchemy2.shape import to_shape
from .. import db
from ..email import send_email
from ..carpool.views import (
    cancel_carpool,
    email_driver_rider_cancelled_request,
)
from ..models import (
    Carpool,
    Destination,
    Person,
    Role,
    PersonRole,
    RideRequest,
)


@admin_bp.route('/admin/')
def admin_index():
    return render_template(
        'admin/index.html',
    )


@admin_bp.route('/admin/stats/')
def admin_stats():
    return render_template(
        'admin/stats.html',
        carpool_count=Carpool.query.count(),
        ride_request_count_approved=RideRequest.query.filter_by(status='approved').count(),
        ride_request_count_requested=RideRequest.query.filter_by(status='requested').count(),
        destination_count=Destination.query.count(),
        driver_count=Carpool.query.distinct(Carpool.driver_id).count(),
    )


@admin_bp.route('/admin/users/<uuid>')
def user_show(uuid):
    user = Person.uuid_or_404(uuid)
    return render_template(
        'admin/users/show.html',
        user=user,
    )


@admin_bp.route('/admin/users/<uuid>/purge', methods=['GET', 'POST'])
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


@admin_bp.route('/admin/users/<user_uuid>/togglerole', methods=['POST'])
def user_toggle_role(user_uuid):
    user = Person.uuid_or_404(user_uuid)
    role = Role.first_by_name_or_404(request.form.get('role_name'))

    if current_user.uuid == user.uuid:
        flash("You cannot modify your own roles", 'error')
        return redirect(url_for('admin.user_show', uuid=user.uuid))

    pr = PersonRole.query.filter_by(person_id=user.id, role_id=role.id).first()
    if pr:
        db.session.delete(pr)
        flash('Role {} removed from this user'.format(role.name), 'success')
    else:
        user.roles.append(role)
        flash('Role {} added to this user'.format(role.name), 'success')
    db.session.commit()

    return redirect(url_for('admin.user_show', uuid=user.uuid))


@admin_bp.route('/admin/users')
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


@admin_bp.route('/admin/drivers_and_riders')
def driver_and_rider_list():
    page = request.args.get('page')
    page = int(page) if page is not None else 1
    per_page = 15

    query = '''
        select d.name destination, cp.leave_time leave_time,
            cp.return_time return_time, 'rider' as rider_driver,
            p.name person_name, p.email email, p.phone_number phone,
            p.preferred_contact_method contact, p.uuid uuid
        from carpools cp, destinations d, people p, riders r
        where cp.destination_id=d.id and cp.id=r.carpool_id and
            r.status='approved' and r.person_id=p.id
        union
        select d.name destination, cp.leave_time leave_time,
            cp.return_time returntime, 'driver' as rider_driver,
            p.name person_name, p.email email, p.phone_number phone,
            p.preferred_contact_method contact, p.uuid uuid
        from carpools cp, destinations d, people p
        where cp.destination_id=d.id and cp.driver_id=p.id
        order by destination, leave_time, person_name
    '''
    result = list(db.engine.execute(query))
    if per_page * page > len(result):
        paginated_result = result[per_page * (page - 1):]
    else:
        paginated_result = result[per_page * (page - 1):per_page * page]
    return render_template(
        'admin/users/drivers_and_riders.html',
        drivers_and_riders=paginated_result,
        page=page,
        not_last=(per_page * page) < len(result),
        not_first=(page > 1)
    )


@admin_bp.route('/admin/users.csv')
def user_list_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Nomad carpool drivers and riders'])
    writer.writerow(['destination', 'carpool leave time', 'carpool return time',
                     'driver/rider', 'name', 'email', 'phone', 'preferred contact method'])

    query = '''
        select d.name destination, cp.leave_time leave_time,
            cp.return_time return_time, 'rider' as rider_driver,
            p.name person_name, p.email email, p.phone_number phone,
            p.preferred_contact_method contact
        from carpools cp, destinations d, people p, riders r
        where cp.destination_id=d.id and cp.id=r.carpool_id and
            r.status='approved' and r.person_id=p.id
        union
        select d.name destination, cp.leave_time leave_time,
            cp.return_time returntime, 'driver' as rider_driver,
            p.name person_name, p.email email, p.phone_number phone,
            p.preferred_contact_method contact
        from carpools cp, destinations d, people p
        where cp.destination_id=d.id and cp.driver_id=p.id
        order by destination, leave_time, person_name
    '''
    for row in db.engine.execute(query):
        writer.writerow([
            row.destination,
            row.leave_time.strftime('%x %X'),
            row.return_time.strftime('%x %X'),
            row.rider_driver,
            row.person_name,
            row.email,
            row.phone,
            row.contact
        ])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-disposition': 'attachment; filename=nomad_users.csv'
        }
    )

@admin_bp.route('/admin/carpools')
def carpool_list():
    page = request.args.get('page')
    page = int(page) if page is not None else None
    per_page = 15

    carpools = Carpool.query.\
        order_by(Carpool.created_at.desc()).\
        paginate(page, per_page)
    return render_template(
        'admin/carpool/list.html',
        carpools=carpools,
    )

@admin_bp.route('/admin/carpools.csv')
def carpool_list_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Nomad carpools'])
    writer.writerow(['from', 'from lat/lon',
                     'destination', 'destination lat/lon', 'destination address',
                     'leave time', 'return time',
                     'driver name', 'drive email',
                     'max riders', 'ride requests', 'approved riders',
                     'status', 'reason for cancellation'
                     ])

    query = '''
        select cp.from_place as from_place, st_x(cp.from_point) as from_lon, st_y(cp.from_point) as from_lat,
               d.name as destination, st_x(d.point) as destination_lon, st_y(d.point) as destination_lat,
               d.address as destination_address,
               cp.leave_time as leave_time,
               cp.return_time as return_time,
               dp.name as driver_name, dp.email as driver_email,
               cp.max_riders as max_riders,
               cp.canceled as canceled,
               cp.cancel_reason as cancel_reason,
               (select count(*) from riders where carpool_id=cp.id) as request_count,
               (select count(*) from riders where carpool_id=cp.id and status='approved') as approved_count
        from carpools cp
        full outer join destinations d on (cp.destination_id=d.id)
        inner join people dp on (dp.id=cp.driver_id)
    '''
    for row in db.engine.execute(query):
        writer.writerow([
            row.from_place,
            ','.join(map(str, [row.from_lat, row.from_lon])),
            row.destination,
            ','.join(map(str, [row.destination_lat, row.destination_lon])),
            row.destination_address,
            row.leave_time.strftime('%x %X'),
            row.return_time.strftime('%x %X'),
            row.driver_name,
            row.driver_email,
            row.max_riders,
            row.request_count,
            row.approved_count,
            "Canceled" if row.canceled else 'Active',
            row.cancel_reason,
        ])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-disposition': 'attachment; filename=nomad_carpools.csv'
        }
    )


@admin_bp.route('/admin/destinations')
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

        _send_destination_action_email(dest, 'modified', 'modified')

        db.session.commit()
        flash("Your destination was updated", 'success')
        return redirect(url_for('admin.destinations_show', uuid=uuid))

    return render_template(
        'admin/destinations/edit.html',
        form=edit_form,
        dest=dest,
    )


@admin_bp.route('/admin/destinations/<uuid>/delete', methods=['GET', 'POST'])
def destinations_delete(uuid):
    dest = Destination.uuid_or_404(uuid)

    delete_form = DeleteDestinationForm()
    if delete_form.validate_on_submit():
        if delete_form.submit.data:
            _send_destination_action_email(dest, 'cancelled', 'deleted')
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


def _send_destination_action_email(destination, verb, template_base):
    for carpool in destination.carpools:
        subject = 'Carpool on {} {}'.format(
            carpool.leave_time_formatted,
            verb
        )

        # For carpool riders
        for ride_request in carpool.ride_requests:
            send_email(
                'admin_destination_{}'.format(template_base),
                ride_request.person.email,
                subject,
                destination=destination,
                carpool=carpool,
                person=ride_request.person,
            )

        # For carpool driver
        send_email(
            'admin_destination_{}'.format(template_base),
            carpool.driver.email,
            subject,
            destination=destination,
            carpool=carpool,
            person=carpool.driver,
        )


@admin_bp.route('/admin/destinations/<uuid>/togglehidden', methods=['POST'])
def destinations_toggle_hidden(uuid):
    dest = Destination.uuid_or_404(uuid)

    dest.hidden = not dest.hidden
    db.session.add(dest)
    db.session.commit()

    if dest.hidden:
        flash("Your destination was hidden", 'success')
    else:
        flash("Your destination was unhidden", 'success')

    return redirect(url_for('admin.destinations_show', uuid=uuid))


@admin_bp.route('/admin/emailpreview/<template>')
def email_preview(template):
    # get enough sample data to cover all templates
    carpool = Carpool.query.first()
    data = {
        'destination': carpool.destination,
        'carpool': carpool,
        'person': carpool.driver,
        'rider': Person.query.first(),
        'driver': carpool.driver,
        'ride_request': RideRequest.query.first(),
        'reason': 'Placeholder reason'
    }
    text = render_template('email/{}.txt'.format(template), **data)
    html = render_template('email/{}.html'.format(template), **data)

    return render_template('admin/emailpreview.html', template=template, text=text, html=html)


@admin_bp.route('/admin/<uuid>/cancel', methods=['GET', 'POST'])
def admin_cancel_carpool(uuid):
    carpool = Carpool.uuid_or_404(uuid)

    cancel_form = CancelCarpoolAdminForm()
    if cancel_form.validate_on_submit():
        if cancel_form.submit.data:
            cancel_carpool(carpool, cancel_form.reason.data, notify_driver=True)

            flash('The carpool was cancelled', 'success')

            # TODO: redirect to carpool list page when available
            return redirect(url_for('admin.admin_index'))

        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    return render_template('carpools/cancel.html', form=cancel_form)

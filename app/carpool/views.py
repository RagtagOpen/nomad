import datetime
from flask import (
    abort,
    escape,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from geoalchemy2 import func
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import mapping, Point
from . import pool_bp
from ..email import (
    send_emails,
    catch_and_log_email_exceptions,
    make_email_message,
)
from .forms import (
    CancelCarpoolDriverForm,
    DriverForm,
    RiderForm,
)
from ..models import Carpool, Destination, RideRequest
from .. import db


@pool_bp.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@pool_bp.route('/carpools/find')
def find():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    name = request.args.get('q')

    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        lat = None
        lon = None
        name = None

    return render_template(
        'carpools/find.html',
        loc_name=name,
        loc_lat=lat,
        loc_lon=lon,
    )


@pool_bp.route('/carpools/starts.geojson')
def start_geojson():
    pools = Carpool.query

    if request.args.get('ignore_prior') != 'false':
        pools = pools.filter(Carpool.leave_time >= datetime.datetime.utcnow())

    near_lat = request.args.get('near.lat')
    near_lon = request.args.get('near.lon')
    near_radius = request.args.get('near.radius') or None

    if near_lat and near_lon:
        try:
            near_lat = float(near_lat)
            near_lon = float(near_lon)
        except ValueError:
            abort(400, "Invalid lat/lon format")

        try:
            near_radius = int(near_radius)
        except ValueError:
            abort(400, "Invalid radius format")

        center = from_shape(Point(near_lon, near_lat), srid=4326)

        if near_radius:
            # We're going to say that radius is in meters.
            # The conversion factor here is based on a 40deg latitude
            # (roughly around Virginia)
            radius_degrees = near_radius / 111034.61
            pools.filter(
                func.ST_Distance(Carpool.from_point, center) <= radius_degrees
            )

        pools = pools.order_by(func.ST_Distance(Carpool.from_point, center))

    features = []
    for pool in pools:
        if pool.from_point is None:
            continue

        features.append({
            'type': 'Feature',
            'geometry': mapping(to_shape(pool.from_point)),
            'id': url_for('carpool.details', uuid=pool.uuid, _external=True),
            'properties': {
                'from_place': escape(pool.from_place),
                'to_place': escape(pool.destination.name),
                'seats_available': pool.seats_available,
                'leave_time': pool.leave_time.isoformat(),
                'return_time': pool.return_time.isoformat(),
                'driver_gender': escape(pool.driver.gender),
            },
        })

    feature_collection = {
        'type': 'FeatureCollection',
        'features': features
    }

    return jsonify(feature_collection)


@pool_bp.route('/carpools/mine', methods=['GET', 'POST'])
@login_required
def mine():
    carpools = current_user.get_driving_carpools()

    return render_template('carpools/mine.html', carpools=carpools)


@pool_bp.route('/carpools/new', methods=['GET', 'POST'])
@login_required
def new():
    if not current_user.name:
        flash("Please specify your name before creating a carpool")
        session['next'] = url_for('carpool.new')
        return redirect(url_for('auth.profile'))

    if not current_user.gender:
        flash("Please specify your gender before creating a carpool")
        session['next'] = url_for('carpool.new')
        return redirect(url_for('auth.profile'))

    driver_form = DriverForm()

    visible_destinations = Destination.find_all_visible().all()

    driver_form.destination.choices = [
        (str(r.uuid), r.name) for r in visible_destinations
    ]
    driver_form.destination.choices.insert(0, ('', "Select one..."))

    if driver_form.validate_on_submit():
        dest = Destination.first_by_uuid(driver_form.destination.data)

        departure_datetime = datetime.datetime(
            driver_form.departure_date.data.year,
            driver_form.departure_date.data.month,
            driver_form.departure_date.data.day,
            int(driver_form.departure_hour.data)
        )

        return_datetime = datetime.datetime(
            driver_form.return_date.data.year,
            driver_form.return_date.data.month,
            driver_form.return_date.data.day,
            int(driver_form.return_hour.data)
        )

        c = Carpool(
            from_place=driver_form.departure_name.data,
            from_point='SRID=4326;POINT({} {})'.format(
                driver_form.departure_lon.data,
                driver_form.departure_lat.data),
            destination_id=dest.id,
            leave_time=departure_datetime,
            return_time=return_datetime,
            max_riders=driver_form.vehicle_capacity.data,
            vehicle_description=driver_form.vehicle_description.data,
            notes=driver_form.notes.data,
            driver_id=current_user.id,
        )
        db.session.add(c)
        db.session.commit()

        flash("Thanks for adding your carpool!", 'success')

        return redirect(url_for('carpool.details', uuid=c.uuid))

    return render_template(
        'carpools/add_driver.html',
        form=driver_form,
        destinations=visible_destinations,
    )


@pool_bp.route('/carpools/<uuid>', methods=['GET', 'POST'])
def details(uuid):
    carpool = Carpool.uuid_or_404(uuid)

    return render_template('carpools/show.html', pool=carpool)


@pool_bp.route('/carpools/<uuid>/embed')
def details_embed(uuid):
    carpool = Carpool.uuid_or_404(uuid)

    return render_template('carpools/show_embed.html', pool=carpool)


@pool_bp.route('/carpools/<carpool_uuid>/newrider', methods=['GET', 'POST'])
@login_required
def new_rider(carpool_uuid):
    carpool = Carpool.uuid_or_404(carpool_uuid)

    if carpool.current_user_is_driver:
        flash("You can't request a ride on a carpool you're driving in")
        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    if not current_user.gender:
        flash("Please specify your gender before creating a carpool request")
        session['next'] = url_for('carpool.new_rider', carpool_uuid=carpool.uuid)
        return redirect(url_for('auth.profile'))

    rider_form = RiderForm()
    if rider_form.validate_on_submit():
        if carpool.seats_available < 1:
            flash("There isn't enough space for you on "
                  "this ride. Try another one?", 'error')
            return redirect(url_for('carpool.details', uuid=carpool.uuid))

        if carpool.get_current_user_ride_request():
            flash("You've already requested a seat on "
                  "this ride. Try another one or cancel your "
                  "existing request.", 'error')
            return redirect(url_for('carpool.details', uuid=carpool.uuid))

        rr = RideRequest(
            carpool_id=carpool.id,
            person_id=current_user.id,
            status='requested',
        )
        db.session.add(rr)
        db.session.commit()

        flash("You've been added to the list for this carpool!", 'success')
        _email_driver_ride_requested(carpool, current_user)

        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    return render_template('carpools/add_rider.html', form=rider_form)


@pool_bp.route('/carpools/<carpool_uuid>/request/<request_uuid>/<action>',
               methods=['GET', 'POST'])
@login_required
def modify_ride_request(carpool_uuid, request_uuid, action):
    carpool = Carpool.uuid_or_404(carpool_uuid)
    request = RideRequest.uuid_or_404(request_uuid)

    user_is_driver = (current_user.id == carpool.driver_id)
    user_is_rider = (current_user.id == request.person_id)

    print("User is driver: ", user_is_driver)
    print("User is rider: ", user_is_rider)

    if not (user_is_driver or user_is_rider):
        flash("You can't do anything with this ride request", 'error')
        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    # Technically the carpool arg isn't required here,
    # but it makes the URL prettier so there.

    if request.carpool_id != carpool.id:
        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    # TODO Check who can modify a ride request. Only:
    #      1) the driver modifying their carpool
    #      2) the rider modifying their request
    #      3) an admin?

    # TODO This big messy if block should be a state machine

    if request.status == 'requested':
        if action == 'approve':
            if not user_is_driver:
                flash("That's not your carpool", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))

            request.status = 'approved'
            db.session.add(request)
            db.session.commit()
            flash("You approved their ride request.")
            _email_ride_approved(request)
        elif action == 'deny':
            if not user_is_driver:
                flash("That's not your carpool", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))

            request.status = 'denied'
            db.session.add(request)
            db.session.commit()
            flash("You denied their ride request.")
            _email_ride_denied(request)
        elif action == 'cancel':
            if not user_is_rider:
                flash("That's not your request", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))

            db.session.delete(request)
            db.session.commit()
            flash("You cancelled your ride request.")
            email_driver_rider_cancelled_request(request, carpool,
                                                 current_user)

    elif request.status == 'denied':
        if action == 'approve':
            if not user_is_driver:
                flash("That's not your carpool", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))

            request.status = 'approved'
            db.session.add(request)
            db.session.commit()
            flash("You approved their ride request.")
            _email_ride_approved(request)
        elif action == 'cancel':
            if not user_is_rider:
                flash("That's not your request", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))

            db.session.delete(request)
            db.session.commit()
            flash("You cancelled your ride request.")

    elif request.status == 'approved':
        if action == 'deny':
            if not user_is_driver:
                flash("That's not your carpool", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))

            request.status = 'denied'
            db.session.add(request)
            db.session.commit()
            flash("You denied their ride request.")
            _email_ride_denied(request)
        elif action == 'cancel':
            if not user_is_rider:
                flash("That's not your request", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))

            db.session.delete(request)
            db.session.commit()
            flash("You withdrew from the carpool.")
            email_driver_rider_cancelled_request(request, carpool,
                                                 current_user)

    else:
        flash("You can't do that to the ride request.", "error")

    return redirect(url_for('carpool.details', uuid=carpool.uuid))


@pool_bp.route('/carpools/<uuid>/cancel', methods=['GET', 'POST'])
@login_required
def cancel(uuid):
    carpool = Carpool.uuid_or_404(uuid)

    if carpool.driver_id != current_user.id:
        flash("You cannot cancel a carpool you didn't create", 'error')
        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    cancel_form = CancelCarpoolDriverForm()
    if cancel_form.validate_on_submit():
        if cancel_form.submit.data:

            cancel_carpool(carpool, cancel_form.reason.data)

            flash("Your carpool was cancelled", 'success')

            return redirect(url_for('carpool.index'))
        else:
            return redirect(url_for('carpool.details', uuid=carpool.uuid))

    return render_template('carpools/cancel.html', form=cancel_form)


def cancel_carpool(carpool, reason=None):
    _email_carpool_cancelled(carpool, reason)
    db.session.delete(carpool)
    db.session.commit()


def _email_carpool_cancelled(carpool, reason):
    driver = carpool.driver
    riders = carpool.riders_and_potential_riders
    if not riders:
        return

    if not reason:
        reason = 'Reason not given!'

    subject = 'Carpool session on {} cancelled'.format(carpool.leave_time)

    messages_to_send = [
        make_email_message(
            'carpools/email/carpool_cancelled.html',
            'carpools/email/carpool_cancelled.txt',
            rider.email,
            subject,
            driver=driver,
            rider=rider,
            carpool=carpool,
            reason=reason) for rider in riders
    ]

    with catch_and_log_email_exceptions(messages_to_send):
        send_emails(messages_to_send)


def _email_driver(carpool, current_user, subject, template_name_specifier):
    message_to_send = make_email_message(
        'carpools/email/{}.html'.format(template_name_specifier),
        'carpools/email/{}.txt'.format(template_name_specifier),
        carpool.driver.email,
        subject,
        rider=current_user,
        carpool=carpool)

    with catch_and_log_email_exceptions([message_to_send]):
        send_emails([message_to_send])


def _email_driver_ride_requested(carpool, current_user):
    subject = '{} requested a ride in carpool on {}'.format(
        current_user.name, carpool.leave_time)

    _email_driver(carpool, current_user, subject, 'ride_requested')


def _email_ride_status(request, subject_beginning, template_name_specifier):
    subject = '{} for carpool on {}'.format(subject_beginning,
                                            request.carpool.leave_time)

    message_to_send = make_email_message(
        'carpools/email/ride_{}.html'.format(template_name_specifier),
        'carpools/email/ride_{}.txt'.format(template_name_specifier),
        request.person.email,
        subject,
        rider=current_user,
        carpool=request.carpool)

    with catch_and_log_email_exceptions([message_to_send]):
        send_emails([message_to_send])


def _email_ride_approved(request):
    _email_ride_status(request, 'Ride approved', 'approved')


def _email_ride_denied(request):
    _email_ride_status(request, 'Ride request declined', 'denied')


def email_driver_rider_cancelled_request(request, carpool, current_user):
    if request.status == 'approved':
        _email_driver_rider_cancelled_approved_request(carpool, current_user)
    else:
        _email_driver_rider_cancelled_request(carpool, current_user)


def _email_driver_rider_cancelled_request(carpool, current_user):
    subject = '{} cancelled their request to ride in carpool on {}'.format(
        current_user.name, carpool.leave_time)

    _email_driver(carpool, current_user, subject, 'ride_request_cancelled')


def _email_driver_rider_cancelled_approved_request(carpool, current_user):
    subject = '{} withdrew from the carpool on {}'.format(
        current_user.name, carpool.leave_time)

    _email_driver(carpool, current_user, subject,
                  'approved_ride_request_cancelled')

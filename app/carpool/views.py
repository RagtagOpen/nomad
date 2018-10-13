import datetime
import random
from dateutil import tz
from flask import (
    abort,
    current_app,
    escape,
    flash,
    jsonify,
    make_response,
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
from ..email import send_email
from .forms import (
    CancelCarpoolDriverForm,
    DriverForm,
    RiderForm,
)
from ..models import Carpool, Destination, RideRequest
from .. import db


@pool_bp.route('/robots.txt')
def robotstxt():
    resp = make_response(render_template('robots.txt'))
    resp.headers["Content-type"] = "text/plain"
    return resp


@pool_bp.route('/')
def index():
    return render_template('index.html')


@pool_bp.route('/carpools/find')
def find():
    query = request.args.get('q', '').strip().replace("'", '')

    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
    except ValueError:
        lat = None
        lon = None

    return render_template(
        'carpools/find.html',
        lat=lat,
        lon=lon,
        user_query=query,  # let jinja sanitize
    )


def approximate_location(geometry):
    # 'coordinates': [-121.88632860000001, 37.3382082]
    coord = geometry['coordinates']
    geometry['coordinates'] = [
        round(coord[0], 2) + random.uniform(-.005, .005),
        round(coord[1], 2) + random.uniform(-.005, .005),
    ]
    return geometry


@pool_bp.route('/carpools/starts.geojson')
def start_geojson():
    pools = Carpool.query.filter(Carpool.canceled == False)

    if request.args.get('ignore_prior') != 'false':
        pools = pools.filter(Carpool.leave_time >= datetime.datetime.utcnow())

    try:
        near_lat = request.args.get('near.lat', type=float)
        near_lon = request.args.get('near.lon', type=float)
    except ValueError:
        abort(400, "Invalid lat/lon format")

    max_distance = 80467  # 50 miles in meters
    search_point = 'POINT(%s %s)' % (near_lon, near_lat)

    # ST_DistanceSphere returns minimum distance in meters between two lon/lat geometries
    pools = pools.filter(
        func.ST_DistanceSphere(Carpool.from_point, search_point) <= max_distance
    )
    pools = pools.order_by(func.ST_DistanceSphere(Carpool.from_point, search_point))

    riders = db.session.query(RideRequest.carpool_id,
                              func.count(RideRequest.id).label('pax')).\
        filter(RideRequest.status == 'approved').\
        group_by(RideRequest.carpool_id).\
        subquery('riders')

    pools = pools.filter(Carpool.from_point.isnot(None)).\
        filter(Carpool.destination_id == Destination.id).\
        filter(Destination.hidden.isnot(True)).\
        outerjoin(riders, Carpool.id == riders.c.carpool_id).\
        filter(riders.c.pax.is_(None) | (riders.c.pax < Carpool.max_riders))

    features = []
    dt_format = current_app.config.get('DATE_FORMAT')

    # get the current user's confirmed carpools
    confirmed_carpools = []
    if not current_user.is_anonymous:
        rides = RideRequest.query.filter(RideRequest.status == 'approved').\
            filter(RideRequest.person_id == current_user.id)
        for ride in rides:
            confirmed_carpools.append(ride.carpool_id)
    else:
        # anonymous user can only see 3 results
        pools = pools.limit(3)

    for pool in pools:
        # show real location to driver and confirmed passenger
        geometry = mapping(to_shape(pool.from_point))
        if not current_user.is_anonymous and \
            (pool.driver_id == current_user.id or pool.id in confirmed_carpools):
            is_approximate_location = False
        else:
            is_approximate_location = True
            geometry = approximate_location(geometry)

        features.append({
            'type': 'Feature',
            'geometry': geometry,
            'id': url_for('carpool.details', uuid=pool.uuid, _external=True),
            'properties': {
                'from_place': escape(pool.from_place),
                'to_place': escape(pool.destination.name),
                'seats_available': pool.seats_available,
                'leave_time': pool.leave_time.isoformat(),
                'return_time': pool.return_time.isoformat(),
                'leave_time_human': pool.leave_time.strftime(dt_format),
                'return_time_human': pool.return_time.strftime(dt_format),
                'driver_gender': escape(pool.driver.gender),
                'is_approximate_location': is_approximate_location,
                'destination_id': pool.destination.id,
                'hidden': pool.destination.hidden
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
    carpools = {'future': [], 'past': []}
    # Start with carpools you're driving in
    for carpool in current_user.get_driving_carpools():
        carpools['future' if carpool.future else 'past'].append(carpool)

    # Add in carpools you have ride requests for
    for req in current_user.get_ride_requests_query():
        carpools['future' if req.carpool.future else 'past'].append(req.carpool)

    # Then sort by departure date
    carpools['future'].sort(key=lambda c: c.leave_time)
    carpools['past'].sort(key=lambda c: c.leave_time)

    return render_template('carpools/mine.html', carpools=carpools)


@pool_bp.route('/carpools/new', methods=['GET', 'POST'])
@login_required
def new():
    if not current_user.name:
        flash("Please specify your name before creating a carpool", 'error')
        session['next'] = url_for('carpool.new')
        return redirect(url_for('auth.profile'))

    if not current_user.gender:
        flash("Please specify your gender before creating a carpool", 'error')
        session['next'] = url_for('carpool.new')
        return redirect(url_for('auth.profile'))

    driver_form = DriverForm()

    desired_destination_id = request.args.get('destination_id')
    if desired_destination_id:
        desired_destination = Destination.find_all_visible().filter_by(uuid=desired_destination_id).first()
        if not desired_destination:
            desired_destination_id = None

    visible_destinations = Destination.find_all_visible().all()
    driver_form.destination.choices = [
        (str(r.uuid), r.name) for r in visible_destinations
    ]

    if desired_destination_id:
        driver_form.destination.data = desired_destination_id
    else:
        driver_form.destination.choices.insert(0, ('', "Select one..."))

    if driver_form.validate_on_submit():
        dest = Destination.first_by_uuid(driver_form.destination.data)

        c = Carpool(
            from_place=driver_form.departure_name.data,
            from_point='SRID=4326;POINT({} {})'.format(
                driver_form.departure_lon.data,
                driver_form.departure_lat.data),
            destination_id=dest.id,
            leave_time=driver_form.departure_datetime,
            return_time=driver_form.return_datetime,
            max_riders=driver_form.vehicle_capacity.data,
            vehicle_description=driver_form.vehicle_description.data,
            notes=driver_form.notes.data,
            driver_id=current_user.id,
            from_seed=driver_form.departure_seed.data,
        )
        db.session.add(c)
        db.session.commit()

        flash("Thank you for offering space in your carpool! When nearby volunteers request a ride, you'll be notified automatically to accept or reject them.", 'success')

        return redirect(url_for('carpool.details', uuid=c.uuid))

    elif request.method == 'POST':
        flash("We couldn't save your new carpool. See below for the errors.", 'error')

    return render_template(
        'carpools/add_driver.html',
        form=driver_form,
        destinations=visible_destinations,
    )


@pool_bp.route('/carpools/<uuid>', methods=['GET', 'POST'])
@login_required
def details(uuid):
    carpool = Carpool.uuid_or_404(uuid)

    return render_template('carpools/show.html', pool=carpool)


@pool_bp.route('/carpools/<uuid>/edit', methods=['GET', 'POST'])
@login_required
def edit(uuid):
    carpool = Carpool.uuid_or_404(uuid)

    if carpool.canceled:
        flash("This carpool has been canceled and can no longer be edited.", 'error')
        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    if current_user != carpool.driver:
        flash("You cannot edit a carpool you didn't create.", 'error')
        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    geometry = mapping(to_shape(carpool.from_point))

    driver_form = DriverForm(
        destination=carpool.destination.uuid,
        departure_lat=geometry['coordinates'][1],
        departure_lon=geometry['coordinates'][0],
        departure_name=carpool.from_place,
        departure_date=carpool.leave_time.date(),
        departure_hour=carpool.leave_time.time().hour,
        return_date=carpool.return_time.date(),
        return_hour=carpool.return_time.time().hour,
        vehicle_description=carpool.vehicle_description,
        vehicle_capacity=carpool.max_riders,
        notes=carpool.notes,
        departure_seed=carpool.from_seed,
    )

    visible_destinations = Destination.find_all_visible().all()

    driver_form.destination.choices = [
        (str(r.uuid), r.name) for r in visible_destinations
    ]
    driver_form.destination.choices.insert(0, ('', "Select one..."))

    if driver_form.validate_on_submit():
        dest = Destination.first_by_uuid(driver_form.destination.data)

        carpool.from_place = driver_form.departure_name.data
        carpool.from_point = 'SRID=4326;POINT({} {})'.format(
            driver_form.departure_lon.data,
            driver_form.departure_lat.data)
        carpool.destination_id = dest.id
        carpool.leave_time = driver_form.departure_datetime
        carpool.return_time = driver_form.return_datetime
        carpool.max_riders = driver_form.vehicle_capacity.data
        carpool.vehicle_description = driver_form.vehicle_description.data
        carpool.notes = driver_form.notes.data
        carpool.driver_id = current_user.id
        db.session.add(carpool)
        db.session.commit()

        flash("Your carpool has been updated.", 'success')

        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    return render_template(
        'carpools/edit.html',
        form=driver_form,
        destinations=visible_destinations,
    )


@pool_bp.route('/carpools/<carpool_uuid>/newrider', methods=['GET', 'POST'])
@login_required
def new_rider(carpool_uuid):
    carpool = Carpool.uuid_or_404(carpool_uuid)

    if carpool.canceled:
        flash("This carpool has been canceled and can no longer be edited.", 'error')
        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    if current_user.is_driver(carpool):
        flash("You can't request a ride on a carpool you're driving in", 'error')
        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    if not current_user.gender:
        flash("Please specify your gender before creating a carpool request")
        session['next'] = url_for('carpool.new_rider', carpool_uuid=carpool.uuid)
        return redirect(url_for('auth.profile'))

    # max 10 rides for non-admin users
    if not current_user.has_roles('admin'):
        now = datetime.datetime.now().replace(tzinfo=tz.gettz('UTC'))
        # ride requests in future, active carpools
        pending_req = current_user.get_ride_requests_query().\
            filter(RideRequest.carpool_id == Carpool.id).\
            filter(Carpool.canceled.is_(False)).\
            filter(Carpool.leave_time > now)
        driving = current_user.get_driving_carpools().\
            filter(Carpool.canceled.is_(False)).\
            filter(Carpool.leave_time > now)
        if pending_req.count() + driving.count() >= 10:
            flash('''
                Sorry, you can be in at most ten carpools.
                Please try again after some of your carpools have finished.
            ''', 'error')
            return render_template('carpools/error.html')


    rider_form = RiderForm()
    if rider_form.validate_on_submit():
        if carpool.seats_available < 1:
            flash("There isn't enough space for you on "
                  "this ride. Try another one?", 'error')
            return redirect(url_for('carpool.details', uuid=carpool.uuid))

        if current_user.get_ride_request_in_carpool(carpool):
            flash("You've already requested a seat on "
                  "this ride. Try another one or cancel your "
                  "existing request.", 'error')
            return redirect(url_for('carpool.details', uuid=carpool.uuid))

        rr = RideRequest(
            carpool_id=carpool.id,
            person_id=current_user.id,
            notes=rider_form.notes.data,
            status='requested',
        )
        db.session.add(rr)
        db.session.commit()

        flash("Your ride request has been sent to the driver for approval! "
              "You'll get an email when you are approved.", 'success')
        _email_driver_ride_requested(carpool, rr, current_user)

        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    return render_template('carpools/add_rider.html', form=rider_form)


@pool_bp.route('/carpools/<carpool_uuid>/request/<request_uuid>/<action>',
               methods=['POST'])
@login_required
def modify_ride_request(carpool_uuid, request_uuid, action):
    carpool = Carpool.uuid_or_404(carpool_uuid)

    if carpool.canceled:
        flash("This carpool has been canceled and can no longer be edited.", 'error')
        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    request = RideRequest.uuid_or_404(request_uuid)

    user_is_driver = (current_user.id == carpool.driver_id)
    user_is_rider = (current_user.id == request.person_id)

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
            if not request.carpool.seats_available:
                flash("No seats available", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))
            request.status = 'approved'
            db.session.add(request)
            db.session.commit()
            flash("You approved their ride request.", 'success')
            _email_ride_approved(request)
        elif action == 'deny':
            if not user_is_driver:
                flash("That's not your carpool", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))

            request.status = 'denied'
            db.session.add(request)
            db.session.commit()
            flash("You denied their ride request.", 'success')
            _email_ride_denied(request)
        elif action == 'cancel':
            if not user_is_rider:
                flash("That's not your request", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))

            db.session.delete(request)
            db.session.commit()
            flash("You cancelled your ride request.", 'success')
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
            flash("You approved their ride request.", 'success')
            _email_ride_approved(request)
        elif action == 'cancel':
            if not user_is_rider:
                flash("That's not your request", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))

            db.session.delete(request)
            db.session.commit()
            flash("You cancelled your ride request.", 'success')

    elif request.status == 'approved':
        if action == 'deny':
            if not user_is_driver:
                flash("That's not your carpool", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))

            request.status = 'denied'
            db.session.add(request)
            db.session.commit()
            flash("You denied their ride request.", 'success')
            _email_ride_denied(request)
        elif action == 'cancel':
            if not user_is_rider:
                flash("That's not your request", 'error')
                return redirect(url_for('carpool.details', uuid=carpool.uuid))

            db.session.delete(request)
            db.session.commit()
            flash("You withdrew from the carpool.", 'success')
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

    if carpool.canceled:
        flash("This carpool has been canceled and can no longer be edited.", 'error')
        return redirect(url_for('carpool.details', uuid=carpool.uuid))

    cancel_form = CancelCarpoolDriverForm()
    if cancel_form.validate_on_submit():
        if cancel_form.submit.data:

            cancel_carpool(carpool, cancel_form.reason.data)

            flash("Your carpool was canceled", 'success')

            return redirect(url_for('carpool.mine'))
        else:
            return redirect(url_for('carpool.details', uuid=carpool.uuid))

    return render_template('carpools/cancel.html', form=cancel_form)


def cancel_carpool(carpool, reason=None, notify_driver=False):
    _email_carpool_cancelled(carpool, reason, notify_driver)
    carpool.canceled = True
    carpool.cancel_reason = reason
    db.session.add(carpool)
    db.session.commit()


def _email_carpool_cancelled(carpool, reason, notify_driver):
    driver = carpool.driver
    riders = carpool.riders_and_potential_riders

    if not reason:
        reason = '<reason not given>'

    subject = 'Carpool session on {} cancelled'.format(
        carpool.leave_time_formatted)

    for rider in riders:
        send_email(
            'carpool_cancelled',
            rider.email,
            subject,
            driver=driver,
            rider=rider,
            carpool=carpool,
            reason=reason,
        )

    if notify_driver:
        send_email(
            'carpool_cancelled',
            driver.email,
            subject,
            driver=driver,
            carpool=carpool,
            reason=reason,
            is_driver=True
        )


def _email_driver(carpool, current_user, subject, template_name_specifier, ride_request=None):
    send_email(
        template_name_specifier,
        carpool.driver.email,
        subject,
        rider=current_user,
        carpool=carpool,
        ride_request=ride_request,
    )


def _email_driver_ride_requested(carpool, ride_request, current_user):
    subject = '{} requested a ride in carpool on {}'.format(
        current_user.name, carpool.leave_time_formatted)

    _email_driver(carpool, current_user, subject, 'ride_requested', ride_request)


def _email_ride_status(request, subject_beginning, template_name_specifier):
    subject = '{} for carpool on {}'.format(
        subject_beginning,
        request.carpool.leave_time_formatted
    )

    send_email(
        template_name_specifier,
        request.person.email,
        subject,
        rider=request.person,
        carpool=request.carpool,
    )


def _email_ride_approved(request):
    _email_ride_status(request, 'Ride approved', 'ride_approved')


def _email_ride_denied(request):
    _email_ride_status(request, 'Ride request declined', 'ride_denied')


def email_driver_rider_cancelled_request(request, carpool, current_user):
    if request.status == 'approved':
        _email_driver_rider_cancelled_approved_request(carpool, current_user)
    else:
        _email_driver_rider_cancelled_request(carpool, current_user)


def _email_driver_rider_cancelled_request(carpool, current_user):
    subject = '{} cancelled their request to ride in carpool on {}'.format(
        current_user.name, carpool.leave_time_formatted)

    _email_driver(carpool, current_user, subject, 'ride_request_cancelled')


def _email_driver_rider_cancelled_approved_request(carpool, current_user):
    subject = '{} withdrew from the carpool on {}'.format(
        current_user.name,
        carpool.leave_time_formatted
    )

    _email_driver(carpool, current_user, subject,
                  'approved_ride_request_cancelled')

import logging
import os
import datetime
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_bootstrap import Bootstrap
from flask_caching import Cache
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_mail import (
    Mail,
    Message
)
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from geoalchemy2 import Geometry
from geoalchemy2.shape import from_shape, to_shape
from oauth import OAuthSignIn
from shapely.geometry import mapping
from urlparse import urlparse, urljoin
from wtforms.fields import (
    BooleanField,
    DateTimeField,
    HiddenField,
    IntegerField,
    StringField,
    SubmitField,
)
from wtforms.validators import InputRequired, NumberRange

app = Flask(__name__)

# Config
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'iajgjknrooiajsefkm')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/carpools')
app.config['CACHE_TYPE'] = os.environ.get('CACHE_TYPE', 'simple')
app.config['CACHE_REDIS_URL'] = os.environ.get('REDIS_URL')
app.config['DEBUG'] = os.environ.get('DEBUG', True)
app.config['GOOGLE_MAPS_API_KEY'] = os.environ.get('GOOGLE_MAPS_API_KEY')

# Mail config
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'localhost')
app.config['MAIL_PORT'] = os.environ.get('MAIL_PORT', 25)
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'from@example.com')

app.config['OAUTH_CREDENTIALS'] = {
    'facebook': {
        'id': os.environ.get('FACEBOOK_APP_ID'),
        'secret': os.environ.get('FACEBOOK_APP_SECRET'),
    },
    'google': {
        'id': os.environ.get('GOOGLE_APP_ID'),
        'secret': os.environ.get('GOOGLE_APP_SECRET'),
    },
}

Bootstrap(app)
db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
lm = LoginManager()

cache.init_app(app)
db.init_app(app)
mail = Mail(app)
migrate.init_app(app, db)
lm.init_app(app)
lm.login_view = 'login'

logger = app.logger
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)


# Models
class RideRequest(db.Model):
    __tablename__ = 'riders'

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('people.id'))
    carpool_id = db.Column(db.Integer, db.ForeignKey('carpools.id'))
    person = db.relationship("Person")
    carpool = db.relationship("Carpool")
    created_at = db.Column(db.DateTime(timezone=True),
                           default=datetime.datetime.utcnow)
    status = db.Column(db.String(120))


class Person(UserMixin, db.Model):
    __tablename__ = 'people'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=datetime.datetime.utcnow)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(120))
    name = db.Column(db.String(80))


class Carpool(db.Model):
    __tablename__ = 'carpools'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=datetime.datetime.utcnow)
    from_place = db.Column(db.String(120))
    from_point = db.Column(Geometry('POINT'))
    to_place = db.Column(db.String(120))
    to_point = db.Column(Geometry('POINT'))
    leave_time = db.Column(db.DateTime(timezone=True))
    return_time = db.Column(db.DateTime(timezone=True))
    max_riders = db.Column(db.Integer)
    driver_id = db.Column(db.Integer, db.ForeignKey('people.id'))

    def get_ride_requests_query(self, status=None):
        query = RideRequest.query.filter_by(carpool_id=self.id)

        if status:
            query = query.filter_by(status=status)

        return query

    def get_current_user_ride_request(self):
        if current_user.is_anonymous:
            return False
        else:
            return self.get_ride_requests_query() \
                       .filter_by(person_id=current_user.id) \
                       .first()

    @property
    def current_user_is_driver(self):
        return current_user.id == self.driver_id

    @property
    def driver(self):
        return Person.query.get(self.driver_id)

    @property
    def seats_available(self):
        return self.max_riders - \
               self.get_ride_requests_query('approved').count()


# Forms
class DriverForm(FlaskForm):
    car_size = IntegerField(
        "Number of Seats",
        [
            InputRequired("Please provide the number of seats in your car"),
            NumberRange(1, 10),
        ],
        description="Seats available (besides the driver)",
    )
    leaving_from = StringField(
        "Leaving From",
        [
            InputRequired("Where are you leaving from?"),
        ]
    )
    leaving_from_lat = HiddenField()
    leaving_from_lon = HiddenField()
    depart_time = DateTimeField(
        "Depart Time",
        [
            InputRequired("When are you leaving?"),
        ],
        format='%m/%d/%Y %H:%M',
    )
    going_to = StringField(
        "Going To",
        [
            InputRequired("Where are going to?"),
        ]
    )
    going_to_lat = HiddenField()
    going_to_lon = HiddenField()
    return_time = DateTimeField(
        "Return Time",
        [
            InputRequired("When do you plan to return?"),
        ],
        format='%m/%d/%Y %H:%M',
    )
    submit = SubmitField(u'Add Your Ride')


class RiderForm(FlaskForm):
    gender = StringField(
        "Gender",
        [
            InputRequired("Please enter your gender"),
        ]
    )
    submit = SubmitField(u'Request A Seat')


class ProfileForm(FlaskForm):
    name = StringField(
        "Name",
        [
            InputRequired("Please enter your name"),
        ]
    )
    submit = SubmitField(u'Update Your Profile')


class CancelCarpoolDriverForm(FlaskForm):
    reason = StringField(
        "Reason",
        description="Describe why you're canceling your carpool. "
                    "This will be visible to your riders."
    )
    cancel = SubmitField(u"Nevermind, Go Back")
    submit = SubmitField(u"Cancel Your Ride")


class CancelCarpoolRiderForm(FlaskForm):
    reason = StringField(
        "Reason",
        description="Describe why you're canceling your ride request. "
                    "This will be visible to your driver."
    )
    cancel = SubmitField(u"Nevermind, Go Back")
    submit = SubmitField(u"Cancel Your Ride")


class DateSearchForm(FlaskForm):
    depart_time = DateTimeField("Depart Time")
    return_time = DateTimeField("Return Time")
    submit = SubmitField(u'Search')


@lm.user_loader
def load_user(id):
    return Person.query.get(int(id))


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


def get_redirect_target():
    for target in request.values.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target


# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template(
        'index.html',
    )


@app.route('/carpools/find')
def find_carpool():
    search_form = DateSearchForm()
    depart_time = search_form.depart_time.data
    return_time = search_form.return_time.data

    if depart_time and return_time and depart_time > return_time:
        flash('Depart Time must be before Return Time', 'error')
        pools = Carpool.query
    else:
        pools = _filter_carpools_by_date(depart_time, return_time)

    return render_template(
        'find_carpool.html',
        form=search_form,
        pools=pools,
    )


@app.route('/carpools/starts.geojson')
def carpool_start_geojson():
    pools = Carpool.query.filter(Carpool.leave_time >= datetime.datetime.utcnow())

    features = []
    for pool in pools:
        if pool.from_point is None:
            continue

        features.append({
            'type': 'Feature',
            'properties': {},
            'geometry': mapping(to_shape(pool.from_point)),
        })

    feature_collection = {
        'type': 'FeatureCollection',
        'features': features
    }

    return jsonify(feature_collection)


@app.route('/login')
def login():
    next_url = request.args.get('next')
    if next_url and is_safe_url(next_url):
        session['next'] = next_url

    return render_template(
        'login.html',
    )


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    profile_form = ProfileForm(name=current_user.name)
    if profile_form.validate_on_submit():
        current_user.name = profile_form.name.data
        db.session.add(current_user)
        db.session.commit()

        flash("You updated your profile.", 'success')

        return redirect(url_for('profile'))

    return render_template('profile.html', form=profile_form)


@app.route('/privacy.html')
def privacy():
    return render_template('privacy.html')


@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@app.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    social_id, username, email = oauth.callback()
    if social_id is None:
        flash('Authentication failed.')
        return redirect(url_for('index'))
    user = Person.query.filter_by(social_id=social_id).first()
    if not user:
        user = Person(social_id=social_id, name=username, email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user, True)
    next_url = session.pop('next', None) or url_for('index')
    return redirect(next_url)


@app.route('/carpools/new', methods=['GET', 'POST'])
@login_required
def new_carpool():
    driver_form = DriverForm()
    if driver_form.validate_on_submit():
        c = Carpool(
            from_place=driver_form.leaving_from.data,
            from_point='SRID=4326;POINT({} {})'.format(
                driver_form.leaving_from_lon.data,
                driver_form.leaving_from_lat.data),
            to_place=driver_form.going_to.data,
            to_point='SRID=4326;POINT({} {})'.format(
                driver_form.going_to_lon.data,
                driver_form.going_to_lat.data),
            leave_time=driver_form.depart_time.data,
            return_time=driver_form.return_time.data,
            max_riders=driver_form.car_size.data,
            driver_id=current_user.id,
        )
        db.session.add(c)
        db.session.commit()

        flash("Thanks for adding your carpool!", 'success')

        return redirect(url_for('index'))

    return render_template('add_driver.html', form=driver_form)


@app.route('/carpools/<int:carpool_id>', methods=['GET', 'POST'])
def carpool_details(carpool_id):
    carpool = Carpool.query.get_or_404(carpool_id)

    return render_template('carpool_details.html', pool=carpool)


@app.route('/carpools/<int:carpool_id>/newrider', methods=['GET', 'POST'])
@login_required
def new_carpool_rider(carpool_id):
    carpool = Carpool.query.get_or_404(carpool_id)

    if carpool.current_user_is_driver:
        flash("You can't request a ride on a carpool you're driving in")
        return redirect(url_for('carpool_details', carpool_id=carpool_id))

    rider_form = RiderForm()
    if rider_form.validate_on_submit():
        if carpool.seats_available < 1:
            flash("There isn't enough space for you on "
                  "this ride. Try another one?", 'error')
            return redirect(url_for('carpool_details', carpool_id=carpool_id))

        if carpool.get_current_user_ride_request():
            flash("You've already requested a seat on "
                  "this ride. Try another one or cancel your "
                  "existing request.", 'error')
            return redirect(url_for('carpool_details', carpool_id=carpool_id))

        rr = RideRequest(
            carpool_id=carpool.id,
            person_id=current_user.id,
            status='requested',
        )
        db.session.add(rr)
        db.session.commit()

        flash("You've been added to the list for this carpool!", 'success')

        return redirect(url_for('carpool_details', carpool_id=carpool_id))

    return render_template('add_rider.html', form=rider_form)


@app.route('/carpools/<int:carpool_id>/request/<int:request_id>/<action>',
           methods=['GET', 'POST'])
@login_required
def modify_ride_request(carpool_id, request_id, action):
    # carpool = Carpool.query.get_or_404(carpool_id)
    request = RideRequest.query.get_or_404(request_id)

    # Technically the carpool arg isn't required here,
    # but it makes the URL prettier so there.

    if request.carpool_id != carpool_id:
        return redirect(url_for('carpool_details', carpool_id=carpool_id))

    # TODO Check who can modify a ride request. Only:
    #      1) the driver modifying their carpool
    #      2) the rider modifying their request
    #      3) an admin?

    # TODO This big messy if block should be a state machine

    if request.status == 'requested':
        if action == 'approve':
            request.status = 'approved'
            db.session.add(request)
            db.session.commit()
            flash("You approved their ride request.")
            # TODO Send email notification to rider
        elif action == 'deny':
            request.status = 'denied'
            db.session.add(request)
            db.session.commit()
            flash("You denied their ride request.")
            # TODO Send email notification to rider

    elif request.status == 'denied':
        if action == 'approve':
            request.status = 'approved'
            db.session.add(request)
            db.session.commit()
            flash("You approved their ride request.")
            # TODO Send email notification to rider

    elif request.status == 'approved':
        if action == 'deny':
            request.status = 'denied'
            db.session.add(request)
            db.session.commit()
            flash("You denied their ride request.")
            # TODO Send email notification to rider

    else:
        flash("You can't do that to the ride request.", "error")

    return redirect(url_for('carpool_details', carpool_id=carpool_id))


@app.route('/carpools/<int:carpool_id>/cancelrider', methods=['GET', 'POST'])
@login_required
def cancel_carpool_rider(carpool_id):
    carpool = Carpool.query.get_or_404(carpool_id)

    cancel_form = CancelCarpoolRiderForm()
    if cancel_form.validate_on_submit():
        if cancel_form.submit.data:
            carpool.riders.remove(current_user)
            db.session.commit()

            flash("Your seat request was deleted", 'success')

        return redirect(url_for('carpool_details', carpool_id=carpool_id))

    return render_template('cancel_carpool_rider.html', form=cancel_form)


@app.route('/carpools/<int:carpool_id>/cancel', methods=['GET', 'POST'])
@login_required
def cancel_carpool(carpool_id):
    carpool = Carpool.query.get_or_404(carpool_id)

    cancel_form = CancelCarpoolDriverForm()
    if cancel_form.validate_on_submit():
        if cancel_form.submit.data:
            _email_carpool_cancelled(
                carpool,
                cancel_form.reason.data,
                not app.debug)
            db.session.delete(carpool)
            db.session.commit()

            flash("Your carpool was canceled", 'success')

            return redirect(url_for('index'))
        else:
            return redirect(url_for('carpool_details', carpool_id=carpool_id))

    return render_template('cancel_carpool.html', form=cancel_form)


def _filter_carpools_by_date(leave_time, return_time):
    if leave_time and return_time:
        pools = Carpool.query.filter(
            Carpool.leave_time >= leave_time,
            Carpool.return_time <= return_time
        )
    elif leave_time:
        pools = Carpool.query.filter(
            Carpool.leave_time >= leave_time
        )
    elif return_time:
        pools = Carpool.query.filter(
            Carpool.return_time <= return_time
        )
    else:
        pools = Carpool.query

    return pools


def _email_carpool_cancelled(carpool, reason, send=False):
    driver = carpool.driver
    riders = carpool.riders
    if len(riders) == 0:
        return

    if not reason:
        reason = 'Reason not given!'

    subject = 'Carpool session on {} cancelled'.format(carpool.leave_time)

    # TODO: This should be an HTML template stored elsewhere
    body = '''
        Hello rider,

        Unfortunately, the carpool session for leaving from {} at {} has been
        cancelled.

        The reason given for the cancellation was: {}.

        Please reach out to {} in order to see if they're willing
        to reschedule.
    '''.format(
            carpool.from_place,
            carpool.leave_time,
            reason,
            driver.email)

    if send:
        with mail.connect() as conn:
            for rider in riders:
                msg = Message(recipients=[rider.email],
                              body=body,
                              subject=subject)
                conn.send(msg)
    else:
        for rider in riders:
            logger.info('sent message to {} with subject {} and body {}'.format(
                rider.email, subject, body))

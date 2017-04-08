import logging
import os
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
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
from oauth import OAuthSignIn
from wtforms.fields import (
    BooleanField,
    DateTimeField,
    IntegerField,
    StringField,
    SubmitField,
)
from wtforms.validators import InputRequired, NumberRange, Email

app = Flask(__name__)

# Config
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'iajgjknrooiajsefkm')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite')
app.config['CACHE_TYPE'] = os.environ.get('CACHE_TYPE', 'simple')
app.config['CACHE_REDIS_URL'] = os.environ.get('REDIS_URL')
app.config['DEBUG'] = os.environ.get('DEBUG', True)

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
riders = db.Table(
    'riders',
    db.Column('person_id', db.Integer, db.ForeignKey('people.id')),
    db.Column('carpool_id', db.Integer, db.ForeignKey('carpools.id')),
)


class Person(UserMixin, db.Model):
    __tablename__ = 'people'

    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(120))
    name = db.Column(db.String(80))


class Carpool(db.Model):
    __tablename__ = 'carpools'

    id = db.Column(db.Integer, primary_key=True)
    from_place = db.Column(db.String(120))
    to_place = db.Column(db.String(120))
    leave_time = db.Column(db.DateTime(timezone=True))
    return_time = db.Column(db.DateTime(timezone=True))
    max_riders = db.Column(db.Integer)
    driver_id = db.Column(db.Integer, db.ForeignKey('people.id'))
    riders = db.relationship('Person', secondary=riders)


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


# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    search_form = DateSearchForm()
    depart_time = search_form.depart_time.data
    return_time = search_form.return_time.data

    if depart_time and return_time and depart_time > return_time:
        flash('Depart Time must be before Return Time', 'error')
        pools = Carpool.query
    else:
        pools = _filter_carpools_by_date(depart_time, return_time)

    return render_template(
        'index.html',
        form=search_form,
        pools=pools,
    )


@app.route('/login')
def login():
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
    return redirect(url_for('index'))


@app.route('/carpools/new', methods=['GET', 'POST'])
@login_required
def new_carpool():
    driver_form = DriverForm()
    if driver_form.validate_on_submit():
        c = Carpool(
            from_place=driver_form.leaving_from.data,
            to_place=driver_form.going_to.data,
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
@login_required
def carpool_details(carpool_id):
    carpool = Carpool.query.get_or_404(carpool_id)

    return render_template('carpool_details.html', pool=carpool)


@app.route('/carpools/<int:carpool_id>/newrider', methods=['GET', 'POST'])
@login_required
def new_carpool_rider(carpool_id):
    carpool = Carpool.query.get_or_404(carpool_id)

    rider_form = RiderForm()
    if rider_form.validate_on_submit():
        if len(carpool.riders) + 1 > carpool.max_riders:
            flash("There isn't enough space for you on "
                  "this ride. Try another one?", 'error')
            return redirect(url_for('carpool_details', carpool_id=carpool_id))

        if current_user in carpool.riders:
            flash("You've already requested a seat on "
                  "this ride. Try another one or cancel your "
                  "existing request.", 'error')
            return redirect(url_for('carpool_details', carpool_id=carpool_id))

        carpool.riders.append(current_user)
        db.session.commit()

        flash("You've been added to the list for this carpool!", 'success')

        return redirect(url_for('carpool_details', carpool_id=carpool_id))

    return render_template('add_rider.html', form=rider_form)


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
    driver = Person.query.get(int(carpool.driver_id))
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

import logging
import os
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    url_for,
)
from flask_caching import Cache
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms.fields import StringField, IntegerField, DateTimeField
from wtforms.fields.html5 import EmailField
from wtforms.validators import InputRequired, NumberRange, Email


app = Flask(__name__)

# Config
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'iajgjknrooiajsefkm')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite')
app.config['CACHE_TYPE'] = os.environ.get('CACHE_TYPE', 'simple')
app.config['CACHE_REDIS_URL'] = os.environ.get('REDIS_URL')

db = SQLAlchemy()
migrate = Migrate()
cache = Cache()
cache.init_app(app)
db.init_app(app)
migrate.init_app(app, db)

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


class Person(db.Model):
    __tablename__ = 'people'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
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
    email = EmailField(
        "Your Email",
        [
            InputRequired("Please enter your email"),
            Email("Please enter a valid email"),
        ]
    )
    car_size = IntegerField(
        "Number of Seats",
        [
            InputRequired("Please provide the number of seats in your car"),
            NumberRange(1, 10),
        ]
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
        ]
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
        ]
    )


class RiderForm(FlaskForm):
    email = EmailField(
        "Email",
        [
            InputRequired("Please enter your email"),
            Email("Please enter a valid email"),
        ]
    )


# Routes
@app.route('/')
def home():
    pools = Carpool.query

    return render_template(
        'index.html',
        pools=pools,
    )


@app.route('/carpools/new', methods=['GET', 'POST'])
def new_carpool():
    driver_form = DriverForm()
    if driver_form.validate_on_submit():
        p = Person(email=driver_form.email.data)
        db.session.add(p)
        c = Carpool(
            from_place=driver_form.leaving_from.data,
            to_place=driver_form.going_to.data,
            leave_time=driver_form.depart_time.data,
            return_time=driver_form.return_time.data,
            max_riders=driver_form.car_size.data,
            driver_id=p.id,
        )
        db.session.add(c)
        db.session.commit()

        flash("Thanks for adding your carpool!",
              kind='success')

        return redirect(url_for('home'))

    return render_template('add_driver.html', form=driver_form)


@app.route('/carpools/<int:carpool_id>/newrider', methods=['GET', 'POST'])
def new_carpool_rider(carpool_id):
    carpool = Carpool.query.get_or_404(carpool_id)

    rider_form = RiderForm()
    if rider_form.validate_on_submit():
        if len(carpool.riders) + 1 > carpool.max_riders:
            flash("There isn't enough space for you on "
                  "this ride. Try another one?", kind='error')
            return redirect(url_for('home'))

        p = Person(email=rider_form.email.data)
        db.session.add(p)
        carpool.riders.append(p)
        db.session.commit()

        flash("You've been added to the list for this carpool!",
              kind='success')

        return redirect(url_for('home'))

    return render_template('add_rider.html', form=rider_form)

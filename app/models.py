import datetime
from flask_login import UserMixin, current_user
from geoalchemy2 import Geometry
from . import db, login_manager


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

    CONTACT_EMAIL = 'email'
    CONTACT_CALL = 'call'
    CONTACT_TEXT = 'text'
    CONTACT_METHODS = (
        CONTACT_EMAIL,
        CONTACT_CALL,
        CONTACT_TEXT,
    )

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=datetime.datetime.utcnow)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(120))
    phone_number = db.Column(db.String(14))
    name = db.Column(db.String(80))
    gender = db.Column(db.String(80))
    preferred_contact_method = db.Column(db.String(80))


@login_manager.user_loader
def load_user(id):
    return Person.query.get(int(id))


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
    def riders(self):
        return self.get_ride_requests_query('approved').all()

    @property
    def seats_available(self):
        return self.max_riders - \
               self.get_ride_requests_query('approved').count()

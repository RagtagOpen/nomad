import datetime
import uuid
from dateutil import tz
from flask import abort
from flask_login import AnonymousUserMixin, UserMixin
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from . import db, login_manager


class UuidMixin(object):
    uuid = db.Column(UUID(as_uuid=True), default=uuid4, index=True)

    @classmethod
    def validate_uuid_format(clz, value):
        try:
            uuid.UUID(hex=value, version=4)
        except ValueError:
            return False
        return True

    @classmethod
    def first_by_uuid(clz, uuid):
        return clz.query.filter_by(uuid=uuid).first()

    @classmethod
    def uuid_or_404(clz, uuid):
        if not clz.validate_uuid_format(uuid):
            abort(404)

        return clz.query.filter_by(uuid=uuid).first_or_404()


class RideRequest(db.Model, UuidMixin):
    __tablename__ = 'riders'

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('people.id'))
    carpool_id = db.Column(db.Integer, db.ForeignKey('carpools.id'))
    person = db.relationship("Person")
    carpool = db.relationship("Carpool")
    created_at = db.Column(db.DateTime(timezone=True),
                           default=datetime.datetime.utcnow)
    status = db.Column(db.String(120))
    notes = db.Column(db.Text)


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(24))
    description = db.Column(db.String(120))

    @classmethod
    def first_by_name(clz, name):
        return clz.query.filter_by(name=name).first()

    @classmethod
    def first_by_name_or_404(clz, name):
        return clz.query.filter_by(name=name).first_or_404()


class PersonRole(db.Model):
    __tablename__ = 'people_roles'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=datetime.datetime.utcnow)
    person_id = db.Column(db.Integer, db.ForeignKey('people.id'))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))


class AnonymousUser(AnonymousUserMixin):
    def has_roles(self, *roles):
        return False

    def get_ride_request_in_carpool(self, carpool):
        return None

    def is_driver(self, carpool):
        return False

login_manager.anonymous_user = AnonymousUser


class Person(UserMixin, db.Model, UuidMixin):
    __tablename__ = 'people'

    CONTACT_EMAIL = 'email'
    CONTACT_CALL = 'call'
    CONTACT_TEXT = 'text'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=datetime.datetime.utcnow)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(120))
    phone_number = db.Column(db.String(14))
    name = db.Column(db.String(80))
    gender = db.Column(db.String(80))
    gender_self_describe = db.Column(db.String(80))
    preferred_contact_method = db.Column(db.String(80))

    roles = db.relationship('Role', secondary='people_roles',
                            backref=db.backref('roles',
                                               lazy='dynamic'))

    def get_id(self):
        """ Overiding the UserMixin `get_id()` to give back the uuid. """
        return self.uuid

    def gender_string(self):
        result = self.gender
        if self.gender == 'Self-described':
            result += ' as {}'.format(self.gender_self_describe)
        return result

    def get_ride_requests_query(self, status=None):
        query = RideRequest.query.filter_by(person_id=self.id)

        if status:
            query = query.filter_by(status=status)

        return query

    def get_ride_request_in_carpool(self, carpool):
        return self.get_ride_requests_query().filter_by(carpool_id=carpool.id).first()

    def is_driver(self, carpool):
        return self.id == carpool.driver_id

    def get_driving_carpools(self):
        query = Carpool.query.filter_by(driver_id=self.id)

        return query

    def has_roles(self, *roles):
        requested_role_set = set(roles)
        our_role_set = set(role.name for role in self.roles)

        return requested_role_set.issubset(our_role_set)


@login_manager.user_loader
def load_user(id):
    return Person.first_by_uuid(id)


class Carpool(db.Model, UuidMixin):
    __tablename__ = 'carpools'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=datetime.datetime.utcnow)
    reminder_email_sent_at = db.Column(db.DateTime(timezone=True),
                                       nullable=True)
    from_place = db.Column(db.String(120))
    # Saving the text that was entered in the address autocomplete
    from_seed = db.Column(db.Text)
    from_point = db.Column(Geometry('POINT'))
    leave_time = db.Column(db.DateTime(timezone=True))
    return_time = db.Column(db.DateTime(timezone=True))
    max_riders = db.Column(db.Integer)
    notes = db.Column(db.Text)
    vehicle_description = db.Column(db.Text)
    driver_id = db.Column(db.Integer, db.ForeignKey('people.id'))
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id'))

    ride_requests = relationship("RideRequest", cascade="all, delete-orphan")
    destination = relationship("Destination")
    driver = relationship("Person")

    def get_ride_requests_query(self, statuses=None):
        query = RideRequest.query.filter_by(carpool_id=self.id)

        if statuses:
            query = query.filter(RideRequest.status.in_(statuses))

        return query

    def get_riders(self, statuses):
        requests = self.get_ride_requests_query(statuses).all()

        if not requests:
            return []

        return Person.query.filter(
            Person.id.in_(p.person_id for p in requests)).all()

    @property
    def riders(self):
        return self.get_riders(['approved'])

    @property
    def riders_and_potential_riders(self):
        return self.get_riders(['approved', 'requested'])

    @property
    def seats_available(self):
        return self.max_riders - \
               self.get_ride_requests_query(['approved']).count()

    @property
    def future(self):
        now = datetime.datetime.now().replace(tzinfo=tz.gettz('UTC'))
        return self.leave_time > now


class Destination(db.Model, UuidMixin):
    __tablename__ = 'destinations'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=datetime.datetime.utcnow)
    hidden = db.Column(db.Boolean(), default=False)
    point = db.Column(Geometry('POINT'))
    name = db.Column(db.String(80))
    slug = db.Column(db.String(80), index=True)
    address = db.Column(db.String(300))

    carpools = relationship("Carpool", cascade="all, delete-orphan")

    @classmethod
    def find_all_visible(cls):
        return cls.query.filter(cls.hidden == False).order_by(cls.name)

    @classmethod
    def find_by_slug(cls, slug, include_hidden=False):
        q = cls.query

        if not include_hidden:
            q = q.filter_by(hidden=False)

        return q.filter_by(slug=slug).first()

    def as_geojson(self):
        """ Returns a GeoJSON Feature object for this Destination. """
        return {
            "type": "Feature",
            "properties": {
                "name": self.name,
                "address": self.address,
            },
            "geometry": mapping(to_shape(self.point))
        }

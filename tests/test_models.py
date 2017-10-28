# -*- coding: utf-8 -*-
"""Model unit tests."""
import datetime as dt

import pytest

import flask_login.utils

from app.models import Person, RideRequest, Role

from .factories import CarpoolFactory, PersonFactory


@pytest.mark.usefixtures('db')
class TestPerson:
    """Person tests."""

    def test_created_at_defaults_to_datetime(self, db):
        """Test creation date."""
        person = Person(social_id='foo', email='foo@bar.com')
        db.session.add(person)
        db.session.commit()
        assert bool(person.created_at)
        assert isinstance(person.created_at, dt.datetime)

    def test_factory(self, db):
        """Test person factory."""
        person = PersonFactory(email='foo@bar.com')
        db.session.commit()
        assert bool(person.social_id)
        assert bool(person.email)
        assert bool(person.created_at)

    def test_get_id(self):
        person = PersonFactory()
        assert person.get_id() == person.uuid

    def test_gender_string(self):
        person = PersonFactory(gender='Female')
        assert person.gender_string() == person.gender

    def test_gender_string_self_describe(self):
        person = PersonFactory(gender='Self-described', gender_self_describe='self-described gender')
        assert person.gender_string() == '{} as {}'.format(person.gender, person.gender_self_describe)

    def test_roles(self):
        """Add a role to a user."""
        role = Role(name='admin')
        person = PersonFactory()
        assert role not in person.roles
        assert not person.has_roles('admin')

        person.roles.append(role)
        assert role in person.roles
        assert person.has_roles('admin')


@pytest.mark.usefixtures('db')
class TestCarpool:
    """Carpool tests."""

    def test_get_ride_requests_query(self, db):
        """Test get ride requests query"""
        carpool_1 = CarpoolFactory()
        carpool_2 = CarpoolFactory()

        person = PersonFactory()

        ride_request_1 = RideRequest(
            person = person,
            carpool = carpool_1,
        )
        ride_request_2 = RideRequest(
            person = person,
            carpool = carpool_1,
            status = 'approved',
        )
        ride_request_3 = RideRequest(
            person = person,
            carpool = carpool_2,
            status = 'rejected',
        )

        db.session.add_all([
            carpool_1,
            carpool_2,
            person,
            ride_request_1,
            ride_request_2,
            ride_request_3,
        ])
        db.session.commit()

        all_ride_requests = \
            carpool_1.get_ride_requests_query().all()

        assert len(all_ride_requests) == 2
        assert all_ride_requests[0] is ride_request_1
        assert all_ride_requests[1] is ride_request_2

        approved_ride_requests = \
            carpool_1.get_ride_requests_query([ 'approved' ]).all()

        assert len(approved_ride_requests) == 1
        assert approved_ride_requests[0] is ride_request_2

    def test_get_current_user_ride_request_not_logged_in(self):
        """Test get curent user ride request when user is not logged in"""
        carpool = CarpoolFactory()
        assert carpool.get_current_user_ride_request() == None

    def test_get_current_user_ride_request_logged_in(self, db, monkeypatch):
        carpool = CarpoolFactory()

        person_1 = PersonFactory()
        person_2 = PersonFactory()

        ride_request_1 = RideRequest(
            person = person_2,
            carpool = carpool,
        )
        ride_request_2 = RideRequest(
            person = person_1,
            carpool = carpool,
        )

        db.session.add_all([
            carpool,
            person_1,
            person_2,
            ride_request_1,
            ride_request_2,
        ])
        db.session.commit()

        monkeypatch.setattr(
            flask_login.utils,
            '_get_user',
            lambda: person_1,
        )

        assert carpool.get_current_user_ride_request() is ride_request_2

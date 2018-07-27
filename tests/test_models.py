# -*- coding: utf-8 -*-
"""Model unit tests."""
import datetime as dt

import pytest

import flask_login.utils

from app.models import Person, Role

from .factories import CarpoolFactory, PersonFactory, RideRequestFactory


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


@pytest.mark.usefixtures('db', 'request_context')
class TestCarpool:
    """Carpool tests."""

    def test_get_ride_requests_query(self, db):
        """Test get ride requests query"""
        carpool_1 = CarpoolFactory()
        carpool_2 = CarpoolFactory()

        ride_request_1 = RideRequestFactory(carpool = carpool_1)
        ride_request_2 = RideRequestFactory(
            carpool = carpool_1,
            status = 'approved',
        )
        ride_request_3 = RideRequestFactory(
            carpool = carpool_2,
            status = 'rejected',
        )

        db.session.add_all([
            carpool_1,
            carpool_2,
            ride_request_1,
            ride_request_2,
            ride_request_3,
        ])
        db.session.commit()

        all_ride_requests = \
            carpool_1.get_ride_requests_query().all()

        assert set(all_ride_requests) == { ride_request_1, ride_request_2 }

        approved_ride_requests = \
            carpool_1.get_ride_requests_query([ 'approved' ]).all()

        assert approved_ride_requests == [ ride_request_2 ]

    def test_get_current_user_ride_request_not_logged_in(self):
        """Test get curent user ride request when user is not logged in"""
        carpool = CarpoolFactory()
        assert carpool.get_current_user_ride_request() == None

    def test_get_current_user_ride_request_logged_in(self, db, monkeypatch):
        """Test get curent user ride request when user is logged in"""
        carpool = CarpoolFactory()

        ride_request_1 = RideRequestFactory(carpool = carpool)
        ride_request_2 = RideRequestFactory(carpool = carpool)

        db.session.add_all([
            carpool,
            ride_request_1,
            ride_request_2,
        ])
        db.session.commit()

        monkeypatch.setattr(
            flask_login.utils,
            '_get_user',
            lambda: ride_request_2.person,
        )
        assert carpool.get_current_user_ride_request() is ride_request_2

    def test_current_user_is_driver_not_logged_in(self):
        """Test current user is driver property when user is not logged in"""
        carpool = CarpoolFactory()
        assert carpool.current_user_is_driver == False

    def test_current_user_is_driver_logged_in(self, db, monkeypatch):
        """Test current user is driver property when user is logged in"""
        carpool_1 = CarpoolFactory()
        carpool_2 = CarpoolFactory()

        db.session.add_all([
            carpool_1,
            carpool_2,
        ])
        db.session.commit()

        monkeypatch.setattr(
            flask_login.utils,
            '_get_user',
            lambda: carpool_1.driver,
        )

        assert carpool_1.current_user_is_driver == True
        assert carpool_2.current_user_is_driver == False

    def test_get_when_no_requests(self, db):
        """Test get riders when no ride requests have been made"""
        carpool = CarpoolFactory()
        assert len(carpool.get_riders(['approved'])) == 0

    def test_get_riders(self, db):
        """Test get riders"""
        carpool_1 = CarpoolFactory()
        carpool_2 = CarpoolFactory()

        ride_request_1 = RideRequestFactory(
            carpool = carpool_1,
            status = 'approved',
        )
        ride_request_2 = RideRequestFactory(
            carpool = carpool_1,
            status = 'approved',
        )
        ride_request_3 = RideRequestFactory(
            carpool = carpool_2,
            status = 'rejected',
        )
        ride_request_4 = RideRequestFactory(
            carpool = carpool_2,
            status = 'approved',
        )

        db.session.add_all([
            carpool_1,
            carpool_2,
            ride_request_1,
            ride_request_2,
            ride_request_3,
            ride_request_4,
        ])
        db.session.commit()

        assert len(carpool_1.get_riders(['rejected'])) == 0

        approved_carpool_1_riders = carpool_1.get_riders(['approved'])
        assert set(approved_carpool_1_riders) == {
            ride_request_1.person,
            ride_request_2.person,
        }

        rejected_carpool_2_riders = carpool_2.get_riders(['rejected'])

        assert rejected_carpool_2_riders == [ ride_request_3.person ]

        approved_rejected_carpool_2_riders = carpool_2.get_riders(['approved', 'rejected'])

        assert set(approved_rejected_carpool_2_riders) == {
            ride_request_3.person,
            ride_request_4.person,
        }

    def test_riders_and_potential_riders_properties(self, db):
        """Test riders and potential riders properties"""
        carpool = CarpoolFactory()

        ride_request_1 = RideRequestFactory(
            carpool = carpool,
            status = 'approved',
        )
        ride_request_2 = RideRequestFactory(
            carpool = carpool,
            status = 'requested',
        )

        db.session.add_all([
            carpool,
            ride_request_1,
            ride_request_2,
        ])
        db.session.commit()

        assert carpool.riders == [ ride_request_1.person ]

        assert set(carpool.riders_and_potential_riders) == {
            ride_request_1.person,
            ride_request_2.person,
        }

    def test_seats_available(self, db):
        """test seats available property"""
        carpool = CarpoolFactory(max_riders = 4)

        ride_request_1 = RideRequestFactory(
            carpool = carpool,
            status = 'approved',
        )
        ride_request_2 = RideRequestFactory(
            carpool = carpool,
            status = 'requested',
        )

        db.session.add_all([
            carpool,
            ride_request_1,
            ride_request_2,
        ])
        db.session.commit()

        assert carpool.seats_available == 3

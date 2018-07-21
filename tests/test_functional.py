# -*- coding: utf-8 -*-
"""Functional tests using WebTest.
See: http://webtest.readthedocs.org/
"""
import urllib
from http import HTTPStatus

from flask import url_for, render_template
import flask_login.utils

from .factories import PersonFactory, CarpoolFactory, RideRequestFactory


class TestProfile:
    def test_profile_not_logged_in(self, testapp):
        res = testapp.get('/profile')
        assert res.status_code == HTTPStatus.FOUND
        url = urllib.parse.urlparse(res.headers['Location'])
        assert url.path == url_for('auth.login')
        assert url.query == ''

    def test_profile_logged_in(self, testapp, db, person, monkeypatch):
        monkeypatch.setattr(flask_login.utils, '_get_user', lambda: person)
        res = testapp.get('/profile')
        assert res.status_code == HTTPStatus.OK
        form = res.forms[1]
        form['name'] = 'foo'
        form['gender'] = 'Female'
        form['preferred_contact'] = 'email'
        res = form.submit('submit')
        assert person.name == 'foo'
        assert person.gender == 'Female'
        assert person.preferred_contact_method == 'email'


class TestEmailTemplates:
    def test_ride_requested(self, db):
        rider = PersonFactory()
        carpool = CarpoolFactory(from_place='from')
        db.session.add(rider)
        db.session.add(carpool)
        db.session.commit()
        rendered = render_template(
            'email/ride_requested.html',
            carpool=carpool,
            rider=rider,
        )
        assert 'requested a ride in your carpool from from to dest' in rendered

    def test_ride_approved(self, db):
        rider = PersonFactory()
        carpool = CarpoolFactory(from_place='from')
        db.session.add(rider)
        db.session.add(carpool)
        db.session.commit()
        rendered = render_template(
            'email/ride_approved.html',
            carpool=carpool,
            rider=rider,
        )
        assert 'approved your request to join the carpool' in rendered
        assert 'Pickup: from' in rendered
        assert 'Destination name: dest' in rendered
        assert 'Destination address: 123 fake street' in rendered

    def test_ride_denied(self, db):
        rider = PersonFactory()
        carpool = CarpoolFactory(from_place='from')
        db.session.add(rider)
        db.session.add(carpool)
        db.session.commit()
        rendered = render_template(
            'email/ride_denied.html',
            carpool=carpool,
            rider=rider,
        )
        assert 'declined your request to join the carpool from from to dest' in rendered

    def test_admin_cancelled(self, db):
        driver = PersonFactory()
        db.session.add(driver)
        carpool = CarpoolFactory(from_place='from', driver=driver)
        db.session.add(carpool)
        rider = PersonFactory()
        db.session.add(rider)
        ride_request = RideRequestFactory(person=rider, carpool=carpool)
        db.session.add(ride_request)
        db.session.commit()
        rendered = render_template(
            'email/carpool_cancelled.html',
            driver=driver,
            rider=rider,
            carpool=carpool,
            is_driver=True,
            reason='test_admin_cancelled',
            person=driver,
        )
        assert 'carpool was cancelled by an administrator' in rendered
        assert 'test_admin_cancelled' in rendered
        assert 'driver gave the following reason' not in rendered


    def test_driver_cancelled(self, db):
        driver = PersonFactory()
        db.session.add(driver)
        carpool = CarpoolFactory(from_place='from', driver=driver)
        db.session.add(carpool)
        rider = PersonFactory()
        db.session.add(rider)
        ride_request = RideRequestFactory(person=rider, carpool=carpool)
        db.session.add(ride_request)
        db.session.commit()
        rendered = render_template(
            'email/carpool_cancelled.html',
            driver=driver,
            rider=rider,
            carpool=carpool,
            reason='test_driver_cancelled',
            person=rider,
        )
        assert 'carpool was cancelled by an administrator' not in rendered
        assert 'test_driver_cancelled' in rendered
        assert 'driver gave the following reason' in rendered

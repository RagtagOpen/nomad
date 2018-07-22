# -*- coding: utf-8 -*-
"""Functional tests using WebTest.
See: http://webtest.readthedocs.org/
"""
import urllib
from http import HTTPStatus

from flask import url_for, render_template
import flask_login.utils

from .factories import PersonFactory, CarpoolFactory, DestinationFactory


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
        config = {
            'BRANDING_LIABILITY_URL': 'liability.html',
            'BRANDING_EMAIL_SIGNATURE': '-- Test Team',
        }
        rendered = render_template(
            'email/ride_approved.html',
            carpool=carpool,
            rider=rider,
            config=config,
        )
        assert 'approved your request to join the carpool' in rendered
        assert 'Pickup: from' in rendered
        assert 'Destination name: dest' in rendered
        assert 'Destination address: 123 fake street' in rendered
        for key in config:
            assert config[key] in rendered

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

    def test_email_signature(self, db):
        templates = [
            'admin_destination_deleted', 'admin_destination_modified',
            'approved_ride_request_cancelled', 'carpool_cancelled', 'driver_reminder',
            'ride_approved', 'ride_denied', 'ride_request_cancelled',
            'ride_requested', 'rider_reminder']
        config = {
            'BRANDING_EMAIL_SIGNATURE': '-- Test Team',
        }
        rider = PersonFactory()
        db.session.add(rider)
        driver = PersonFactory()
        db.session.add(driver)
        carpool = CarpoolFactory(from_place='from')
        db.session.add(carpool)
        destination = DestinationFactory()
        db.session.add(destination)
        db.session.commit()
        for ext in ['html', 'txt']:
            for template in templates:
                template_path = 'email/%s.%s' % (template, ext)
                print(template_path)
                rendered = render_template(
                    template_path,
                    config=config,
                    carpool=carpool,
                    rider=rider,
                    driver=driver,
                    person=rider,
                    destination=destination,
                )
                assert config['BRANDING_EMAIL_SIGNATURE'] in rendered, \
                    '%s missing signature' % template_path

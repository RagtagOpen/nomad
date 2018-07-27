# -*- coding: utf-8 -*-
"""Functional tests using WebTest.
See: http://webtest.readthedocs.org/
"""
import urllib
from http import HTTPStatus

from app.auth.oauth import OAuthSignIn
from flask import request

from .factories import PersonFactory, CarpoolFactory, DestinationFactory, RideRequestFactory

# A Mock OAuth Provider. Allows for users to be logged in
class MockSignIn(OAuthSignIn):
    def __init__(self):
        self.provider_name = 'mock'

    def authorize(self):
        pass

    def callback(self):
        return (
            request.args.get('id'),
            request.args.get('name'),
            request.args.get('email'),
        )

def login(testapp, social_id, user_name, user_email):
    testapp.get('/callback/mock', params=dict(id=social_id, name=user_name, email=user_email))

def login_person(testapp, person):
    login(testapp, person.social_id, person.name, person.email)


class TestProfile:
    def test_profile_not_logged_in(self, testapp):
        res = testapp.get('/profile')
        assert res.status_code == HTTPStatus.FOUND
        url = urllib.parse.urlparse(res.headers['Location'])
        assert url.path == '/login'
        assert url.query == ''

    def test_profile_logged_in(self, testapp, db, person):
        login_person(testapp, person)
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

    def test_profile_blocked_is_logged_out(self, testapp, db, person, blocked_role):
        login_person(testapp, person)
        person.roles.append(blocked_role)
        print(person.is_active)
        db.session.commit()
        res = testapp.get('/profile')
        assert res.status_code == HTTPStatus.FOUND
        url = urllib.parse.urlparse(res.headers['Location'])
        assert url.path == '/login'
        assert url.query == ''

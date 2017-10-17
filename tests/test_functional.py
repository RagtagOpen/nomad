# -*- coding: utf-8 -*-
"""Functional tests using WebTest.
See: http://webtest.readthedocs.org/
"""
import urllib
from http import HTTPStatus

from flask import url_for
import flask_login.utils

from app.models import Person

from .factories import PersonFactory


class TestProfile:
    def test_profile_not_logged_in(self, testapp):
        res = testapp.get('/profile')
        assert res.status_code == HTTPStatus.FOUND
        url = urllib.parse.urlparse(res.headers['Location'])
        assert url.path == url_for('auth.login')
        assert url.query == 'next=%2Fprofile'

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

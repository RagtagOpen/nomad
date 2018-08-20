# -*- coding: utf-8 -*-
import urllib
from http import HTTPStatus

from . import login_person
from ..factories import (CarpoolFactory, DestinationFactory, PersonFactory,
                         RideRequestFactory)


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
        form = res.forms['update-profile-form']
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
        db.session.commit()
        res = testapp.get('/profile')
        assert res.status_code == HTTPStatus.FOUND
        url = urllib.parse.urlparse(res.headers['Location'])
        assert url.path == '/login'
        assert url.query == ''

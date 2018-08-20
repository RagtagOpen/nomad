from . import login, login_person
from ..factories import PersonFactory
from http import HTTPStatus
import urllib


class TestLoginFlow:
    def test_redirect_on_login(self, testapp, db, person, carpool):
        cancel_carpool_url = '/carpools/{}/cancel'.format(carpool.uuid)
        res = testapp.get(cancel_carpool_url)
        res = res.follow()
        res = login_person(testapp, person, follow=False)
        assert res.status_code == HTTPStatus.FOUND
        url = urllib.parse.urlparse(res.headers['Location'])
        assert url.path == cancel_carpool_url

    def test_dupe_email_login(self, testapp, db, person, carpool):
        # Steve logs in once using his Facebook account
        res = login(testapp, 'steve@facebook', 'stevejobs', 'steve@example.com')
        assert res.status_code == HTTPStatus.FOUND
        url = urllib.parse.urlparse(res.headers['Location'])
        assert url.path == '/profile'

        # ... then logs out
        res = testapp.post('/logout')
        assert res.status_code == HTTPStatus.FOUND
        url = urllib.parse.urlparse(res.headers['Location'])
        assert url.path == '/'

        # Steve tries to login again, this time using Google
        res = login(testapp, 'steve@google', 'stevejobs', 'steve@example.com')
        assert res.status_code == HTTPStatus.FOUND
        url = urllib.parse.urlparse(res.headers['Location'])
        assert url.path == '/'

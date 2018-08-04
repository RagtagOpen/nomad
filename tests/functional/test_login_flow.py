from . import login_person
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

from datetime import timedelta
from . import login_person
from http import HTTPStatus
import urllib
import datetime


class TestCarpool:
    def test_carpool_creation(self, testapp, db, full_person, destination):
        home = login_person(testapp, full_person).follow()
        new_carpool = home.click('Give a ride', index=0)
        form = new_carpool.forms[1]
        form['destination'] = destination.uuid
        # If we're using some sort of webdriver, we could actually integrate with a map
        form.set('departure_lat', '40.7128', index=0)
        form.set('departure_lon', '-74.0060', index=0)
        form['departure_name'] = 'NYC'
        form['departure_date'] = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        form['departure_hour'] = '9'
        form['return_date'] = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        form['return_hour'] = '18'
        res = form.submit('submit').follow()
        print(res)
        assert res.status_code == HTTPStatus.OK
        assert "Thank you for offering space in your carpool" in res
        assert "You're the driver of this carpool!" in res
        my_page = testapp.get('/carpools/mine')
        assert "NYC" in my_page
        assert "You’re the driver of this carpool. Thanks for driving!" in my_page

    def test_carpool_join(self, testapp, db, full_person, carpool):
        home = login_person(testapp, full_person).follow()
        # Not testing the ride finder because it's JS. If we use a real browser, then we can test it
        carpool_page = testapp.get('/carpools/{}'.format(carpool.uuid))
        confirmation_page = carpool_page.click("Request a seat in carpool")
        new_carpool_page = confirmation_page.forms[1].submit("Request A Seat").follow()
        assert "Your ride request is pending." in new_carpool_page
        my_page = testapp.get('/carpools/mine')
        assert carpool.destination.name in my_page
        assert "Your ride request is pending. We’re waiting for your driver to confirm." in my_page
        # make carpool in past; no details
        carpool.leave_time = carpool.leave_time - timedelta(days=100)
        db.session.commit()
        my_page = testapp.get('/carpools/mine')
        assert carpool.destination.name in my_page
        assert "Your ride request is pending." not in my_page

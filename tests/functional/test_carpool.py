import http
import urllib
from datetime import date, datetime, timedelta
from dateutil import tz
from http import HTTPStatus

from flask import url_for
from freezegun import freeze_time

from app.models import PersonRole
from . import login_person
from ..factories import CarpoolFactory, RideRequestFactory, RoleFactory

def register_for_carpool(testapp, carpool_uuid):
    carpool_page = testapp.get('/carpools/{}'.format(carpool_uuid))
    confirmation_page = carpool_page.click("Request a seat in carpool", index=0)
    return confirmation_page.forms['join-carpool-form'].submit("Request A Seat").follow()


def request_carpool_seat(testapp, carpool_uuid):
    carpool_page = testapp.get('/carpools/{}'.format(carpool_uuid))
    return carpool_page.click("Request a seat in carpool", index=0)


def create_carpool_for_tomorrow(testapp, destination):
    new_carpool = testapp.get('/carpools/new')
    form = new_carpool.forms['new-carpool-form']
    form['destination'] = destination.uuid
    # If we're using some sort of webdriver, we could actually integrate with a map
    form.set('departure_lat', '40.7128', index=0)
    form.set('departure_lon', '-74.0060', index=0)
    form['departure_name'] = 'NYC'
    form['departure_date'] = (date.today() + timedelta(days=1)).isoformat()
    form['departure_hour'] = '9'
    form['return_date'] = (date.today() + timedelta(days=1)).isoformat()
    form['return_hour'] = '18'
    return form.submit('submit').follow()


class TestCarpool:
    def test_carpool_creation(self, testapp, db, full_person, destination):
        home = login_person(testapp, full_person)
        res = create_carpool_for_tomorrow(testapp, destination)
        assert res.status_code == HTTPStatus.OK
        assert "Thank you for offering space in your carpool" in res
        assert "You're the driver of this carpool!" in res
        my_page = testapp.get('/carpools/mine')
        assert "NYC" in my_page
        assert "You’re the driver of this carpool. Thanks for driving!" in my_page

    def test_carpool_requires_auth(self, testapp, db, request_context):
        """Regression test for #703"""
        resp = testapp.get('/carpools/7e39797a')
        assert resp.status_code == http.HTTPStatus.FOUND
        location = urllib.parse.urlparse(resp.headers['Location'])
        assert location.path == url_for('auth.login')

    def test_carpool_flow(self, testapp, db, full_person, carpool):
        home = login_person(testapp, full_person)
        # Not testing the ride finder because it's JS. If we use a real browser, then we can test it
        new_carpool_page = register_for_carpool(testapp, carpool.uuid)
        assert "Your ride request is pending." in new_carpool_page

        my_page = testapp.get('/carpools/mine')
        assert carpool.destination.name in my_page
        assert "Your ride request is pending. We’re waiting for your driver to confirm." in my_page

        # Driver's App
        testapp.reset()
        person_2 = carpool.driver
        person_2.name = "John Smith"
        person_2.gender = "Male"
        db.session.commit()
        person_2_home = login_person(testapp, person_2)
        new_carpool = person_2_home.click('Give a ride', index=0)
        driver_carpool_page = testapp.get('/carpools/{}'.format(carpool.uuid))
        approve_form = driver_carpool_page.forms['approve-rider-form']
        driver_confirmation_page = approve_form.submit().follow()
        assert "You approved their ride request" in driver_confirmation_page

        # Back in the Passenger's App
        testapp.reset()
        home = login_person(testapp, full_person)
        carpool_page = testapp.get('/carpools/{}'.format(carpool.uuid))
        assert "You are confirmed for this carpool" in carpool_page

    def test_old_carpools_disappear(self, testapp, full_person, destination):
        login_person(testapp, full_person)
        create_carpool_for_tomorrow(testapp, destination)

        with freeze_time(date.today() + timedelta(days=3)):
            my_page = testapp.get('/carpools/mine')
            assert "You have no upcoming carpools!" in my_page
            past_carpools = my_page.html.find(
                "div", {"class": "carpools past"})
            assert destination.name in past_carpools.text
            future_carpools = my_page.html.find(
                "div", {"class": "carpools future"})
            assert destination.name not in future_carpools.text

    def test_ride_limit(self, testapp, db, full_person):
        # create 13 future active carpools
        carpools = []
        now = datetime.now().replace(tzinfo=tz.gettz('UTC'))
        leave_time = now + timedelta(days=1)
        # create carpools 0-3 as driver
        for _ in range(4):
            return_time = leave_time + timedelta(days=1)
            carpools.append(CarpoolFactory(leave_time=leave_time, return_time=return_time,
                                           driver=full_person))
            leave_time = leave_time + timedelta(days=1)
        # create carpools 4-12 for use as passenger
        for _ in range(4, 13):
            return_time = leave_time + timedelta(days=1)
            carpools.append(CarpoolFactory(leave_time=leave_time, return_time=return_time))
            leave_time = leave_time + timedelta(days=1)
        # create ride requests for carpools 4-9
        for i in range(4, 10):
            RideRequestFactory(person=full_person, carpool=carpools[i])

        error_msg = 'Sorry, you can be in at most ten carpools.'
        confirm_msg = 'Confirm your details'

        # 10 carpools (4 driver, 6 passenger): request a ride as regular user returns error
        login_person(testapp, full_person)
        result = request_carpool_seat(testapp, carpools[10].uuid)
        assert error_msg in result

        # cancel carpool 0
        carpools[0].canceled = True
        db.session.add(carpools[0])
        db.session.commit()
        # now 9 ride requests: request a ride ok
        result = request_carpool_seat(testapp, carpools[10].uuid)
        assert confirm_msg in result

        # set carpool date to past
        carpools[4].leave_time = datetime.now() - timedelta(days=1)
        db.session.add(carpools[4])
        db.session.commit()
        # now 9 carpools: request ride ok
        result = request_carpool_seat(testapp, carpools[11].uuid)
        assert confirm_msg in result

        # now 10 carpools: request a ride as admin ok
        admin_role = RoleFactory(name='admin')
        db.session.add(PersonRole(person_id=full_person.id, role_id=admin_role.id))
        db.session.commit()
        result = request_carpool_seat(testapp, carpools[12].uuid)
        assert confirm_msg in result

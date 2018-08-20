import urllib
from datetime import date, datetime, timedelta
from http import HTTPStatus

from freezegun import freeze_time

from . import login_person


def register_for_carpool(testapp, carpool_uuid):
    carpool_page = testapp.get('/carpools/{}'.format(carpool_uuid))
    confirmation_page = carpool_page.click("Request a seat in carpool")
    return confirmation_page.forms['join-carpool-form'].submit("Request A Seat").follow()


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

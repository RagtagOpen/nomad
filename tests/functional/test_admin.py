from http import HTTPStatus

from . import login_person
from ..factories import CarpoolFactory, RideRequestFactory, DestinationFactory, PersonFactory


class TestAdmin:
    def test_admin_user_can_access_admin(self, testapp, db, person, admin_role):
        person.roles.append(admin_role)
        db.session.commit()
        login_person(testapp, person)
        res = testapp.get('/admin/')
        assert res.status_code == HTTPStatus.OK

    def test_non_admin_user_cannot_access_admin(self, testapp, db, person):
        login_person(testapp, person)
        res = testapp.get('/admin/', status=HTTPStatus.FORBIDDEN)

    def test_driver_rider_csv(self, testapp, db, person, admin_role):
        # Set up rider and driver
        rider, driver = PersonFactory(), PersonFactory()
        carpool = CarpoolFactory(driver=driver)
        destination = DestinationFactory(carpools=[carpool])
        request = RideRequestFactory(carpool=carpool, person=rider, status='approved')

        person.roles.append(admin_role)
        db.session.commit()
        login_person(testapp, person)

        res = testapp.get('/admin/users.csv')
        assert res.status_code == HTTPStatus.OK
        lines = res.body.decode().splitlines()
        assert len(lines) == 4
        headers = lines[1].split(',')
        rows = [
            dict(zip(headers, line.split(',')))
            for line in lines[2:]
        ]
        assert rows[0]['carpool_id'] == str(carpool.id)
        assert rows[0]['driver/rider'] == 'rider'
        assert rows[0]['name'] == rider.name
        assert rows[1]['carpool_id'] == str(carpool.id)
        assert rows[1]['driver/rider'] == 'driver'
        assert rows[1]['name'] == driver.name

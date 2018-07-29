from . import login_person
from http import HTTPStatus


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

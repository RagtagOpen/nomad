import pytest
from .factories import PersonFactory, CarpoolFactory, RideRequestFactory, DestinationFactory
from flask import render_template


@pytest.mark.usefixtures('request_context')
class TestEmailTemplates:
    def test_ride_requested(self, db):
        rider = PersonFactory()
        carpool = CarpoolFactory(from_place='from')
        db.session.add(rider)
        db.session.add(carpool)
        db.session.commit()
        rendered = render_template(
            'email/ride_requested.html',
            carpool=carpool,
            rider=rider,
        )
        assert 'requested a ride in your carpool from from to dest' in rendered

    def test_ride_approved(self, db):
        rider = PersonFactory()
        carpool = CarpoolFactory(from_place='from')
        db.session.add(rider)
        db.session.add(carpool)
        db.session.commit()
        config = {
            'BRANDING_LIABILITY_URL': 'liability.html',
            'BRANDING_EMAIL_SIGNATURE': '-- Test Team',
        }
        rendered = render_template(
            'email/ride_approved.html',
            carpool=carpool,
            rider=rider,
            config=config,
        )
        assert 'approved your request to join the carpool' in rendered
        assert 'Pickup: from' in rendered
        assert 'Destination name: dest' in rendered
        assert 'Destination address: 123 fake street' in rendered
        for key in config:
            assert config[key] in rendered

    def test_ride_denied(self, db):
        rider = PersonFactory()
        carpool = CarpoolFactory(from_place='from')
        db.session.add(rider)
        db.session.add(carpool)
        db.session.commit()
        rendered = render_template(
            'email/ride_denied.html',
            carpool=carpool,
            rider=rider,
        )
        assert 'declined your request to join the carpool from from to dest' in rendered

    def test_email_signature(self, db):
        templates = [
            'admin_destination_deleted', 'admin_destination_modified',
            'approved_ride_request_cancelled', 'carpool_cancelled', 'driver_reminder',
            'ride_approved', 'ride_denied', 'ride_request_cancelled',
            'ride_requested', 'rider_reminder']
        config = {
            'BRANDING_EMAIL_SIGNATURE': '-- Test Team',
        }
        rider = PersonFactory()
        db.session.add(rider)
        driver = PersonFactory()
        db.session.add(driver)
        carpool = CarpoolFactory(from_place='from')
        db.session.add(carpool)
        destination = DestinationFactory()
        db.session.add(destination)
        db.session.commit()
        for ext in ['html', 'txt']:
            for template in templates:
                template_path = 'email/%s.%s' % (template, ext)
                print(template_path)
                rendered = render_template(
                    template_path,
                    config=config,
                    carpool=carpool,
                    rider=rider,
                    driver=driver,
                    person=rider,
                    destination=destination,
                )
                assert config['BRANDING_EMAIL_SIGNATURE'] in rendered, \
                    '%s missing signature' % template_path

    def test_admin_cancelled(self, db):
        driver = PersonFactory()
        db.session.add(driver)
        carpool = CarpoolFactory(from_place='from', driver=driver)
        db.session.add(carpool)
        rider = PersonFactory()
        db.session.add(rider)
        ride_request = RideRequestFactory(person=rider, carpool=carpool)
        db.session.add(ride_request)
        db.session.commit()
        rendered = render_template(
            'email/carpool_cancelled.html',
            driver=driver,
            rider=rider,
            carpool=carpool,
            is_driver=True,
            reason='test_admin_cancelled',
            person=driver,
        )
        assert 'carpool was cancelled by an administrator' in rendered
        assert 'test_admin_cancelled' in rendered
        assert 'driver gave the following reason' not in rendered

    def test_driver_cancelled(self, db):
        driver = PersonFactory()
        db.session.add(driver)
        carpool = CarpoolFactory(from_place='from', driver=driver)
        db.session.add(carpool)
        rider = PersonFactory()
        db.session.add(rider)
        ride_request = RideRequestFactory(person=rider, carpool=carpool)
        db.session.add(ride_request)
        db.session.commit()
        rendered = render_template(
            'email/carpool_cancelled.html',
            driver=driver,
            rider=rider,
            carpool=carpool,
            reason='test_driver_cancelled',
            person=rider,
        )
        assert 'carpool was cancelled by an administrator' not in rendered
        assert 'test_driver_cancelled' in rendered
        assert 'driver gave the following reason' in rendered

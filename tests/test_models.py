# -*- coding: utf-8 -*-
"""Model unit tests."""
import datetime as dt

import pytest

from app.models import Person, Role

from .factories import PersonFactory


@pytest.mark.usefixtures('db')
class TestPerson:
    """Person tests."""

    def test_created_at_defaults_to_datetime(self, db):
        """Test creation date."""
        person = Person(social_id='foo', email='foo@bar.com')
        db.session.add(person)
        db.session.commit()
        assert bool(person.created_at)
        assert isinstance(person.created_at, dt.datetime)

    def test_factory(self, db):
        """Test person factory."""
        person = PersonFactory(email='foo@bar.com')
        db.session.commit()
        assert bool(person.social_id)
        assert bool(person.email)
        assert bool(person.created_at)

    def test_get_id(self):
        person = PersonFactory()
        assert person.get_id() == person.uuid

    def test_gender_string(self):
        person = PersonFactory(gender='Female')
        assert person.gender_string() == person.gender

    def test_gender_string_self_describe(self):
        person = PersonFactory(gender='Self-described', gender_self_describe='self-described gender')
        assert person.gender_string() == '{} as {}'.format(person.gender, person.gender_self_describe)

    def test_roles(self):
        """Add a role to a user."""
        role = Role(name='admin')
        person = PersonFactory()
        assert role not in person.roles
        assert not person.has_roles('admin')

        person.roles.append(role)
        assert role in person.roles
        assert person.has_roles('admin')

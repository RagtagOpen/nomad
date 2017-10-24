# -*- coding: utf-8 -*-
"""Factories to help in tests."""
import datetime

from factory import Sequence, SubFactory, LazyFunction
from factory.alchemy import SQLAlchemyModelFactory

from app import db
from app.models import Person, Carpool, Destination


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory."""

    class Meta:
        """Factory configuration."""
        abstract = True
        sqlalchemy_session = db.session


class PersonFactory(BaseFactory):
    """Person factory."""
    name = Sequence(lambda n: 'user{0}'.format(n))
    email = Sequence(lambda n: 'user{0}@example.com'.format(n))
    social_id = Sequence(lambda n: 'user{0}'.format(n))

    class Meta:
        """Factory configuration."""
        model = Person


class DestinationFactory(BaseFactory):
    """Carpool factory."""
    name = Sequence(lambda n: 'dest{0}'.format(n))

    class Meta:
        """Factory configuration."""
        model = Destination


class CarpoolFactory(BaseFactory):
    """Carpool factory."""
    leave_time = LazyFunction(datetime.datetime.now)
    destination = SubFactory(DestinationFactory)
    driver = SubFactory(PersonFactory)

    class Meta:
        """Factory configuration."""
        model = Carpool

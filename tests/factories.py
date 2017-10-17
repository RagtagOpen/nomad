# -*- coding: utf-8 -*-
"""Factories to help in tests."""
from factory import PostGenerationMethodCall, Sequence
from factory.alchemy import SQLAlchemyModelFactory

from app import db
from app.models import Person


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory."""

    class Meta:
        """Factory configuration."""

        abstract = True
        sqlalchemy_session = db.session


class PersonFactory(BaseFactory):
    """Person factory."""
    email = Sequence(lambda n: 'user{0}@example.com'.format(n))
    social_id = Sequence(lambda n: 'user{0}'.format(n))

    class Meta:
        """Factory configuration."""
        model = Person

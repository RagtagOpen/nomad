# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""

import pytest
from webtest import TestApp

from app import create_app
from app import db as _db

from .factories import PersonFactory, RoleFactory

@pytest.fixture
def app():
    app = create_app('default')
    context = app.app_context()
    context.push()
    yield app
    context.pop()

@pytest.fixture
def testapp(app):
    """A Webtest app."""
    return TestApp(app)


@pytest.fixture
def request_context(app):
    """A Request Context (for when request-specific information is needed in scope)."""
    with app.test_request_context() as ctx:
        yield ctx


@pytest.fixture
def db(app):
    """A database for the tests."""
    _db.app = app
    _db.create_all()

    yield _db

    # Explicitly close DB connection
    _db.session.close()
    _db.drop_all()


@pytest.fixture
def person(db):
    """A user for the tests."""
    person = PersonFactory()
    db.session.commit()
    return person

@pytest.fixture
def blocked_role(db):
    """A blocked role for the tests."""
    role = RoleFactory(name='blocked')
    db.session.commit()

    return role

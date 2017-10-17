# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""

import pytest
from webtest import TestApp

from app import create_app
from app import db as _db

from .factories import PersonFactory


@pytest.fixture
def app():
    """An application for the tests."""
    _app = create_app('default')
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture
def testapp(app):
    """A Webtest app."""
    return TestApp(app)


@pytest.fixture
def db(app):
    """A database for the tests."""
    _db.app = app
    with app.app_context():
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

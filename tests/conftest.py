# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""
import sqlalchemy
import pytest
from webtest import TestApp

from app import create_app
from app import db as _db

from .factories import PersonFactory, RoleFactory, CarpoolFactory

TEST_DB='testdb'

@pytest.fixture
def app():
    app = create_app('default')
    app.config['SQLALCHEMY_DATABASE_URI'] = test_db_uri()

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

@pytest.fixture(scope='session', autouse=True)
def create_test_db():
    def_app = create_app('default')
    conn = sqlalchemy.create_engine(def_app.config['SQLALCHEMY_DATABASE_URI']).connect()
    conn.execute('commit')

    try:
        conn.execute("create database {}".format(TEST_DB))
    except sqlalchemy.exc.ProgrammingError:
        pass # Ignore if db already exists
    finally:
        conn.close()

    conn = sqlalchemy.create_engine(test_db_uri()).connect()
    conn.execute('create extension if not exists postgis')
    conn.close()

def test_db_uri():
    app = create_app('default')
    parts = app.config['SQLALCHEMY_DATABASE_URI'].split('/')
    return '/'.join(parts[:-1]) + '/' + TEST_DB

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

@pytest.fixture
def carpool(db):
    """A carpool for the tests"""
    carpool = CarpoolFactory()
    db.session.commit()
    return carpool

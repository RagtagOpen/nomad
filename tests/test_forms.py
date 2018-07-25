# -*- coding: utf-8 -*-
"""Test forms."""

from werkzeug.datastructures import MultiDict

from app.auth.forms import ProfileForm
import pytest


@pytest.mark.usefixtures('request_context')
class TestProfileForm:
    """Profile form."""
    def test_validate_name_missing(self, person):
        form = ProfileForm(
            formdata=MultiDict({
                'preferred_contact': 'email',
                'gender': 'Female',
            }),
            meta={'csrf': False},
        )
        assert form.validate() is False

    def test_validate_gender_missing(self, person):
        form = ProfileForm(
            formdata=MultiDict({
                'name': 'foo',
                'preferred_contact': 'email',
            }),
            meta={'csrf': False},
        )
        assert form.validate() is False

    def test_validate_gender_invalid(self, person):
        form = ProfileForm(
            formdata=MultiDict({
                'name': 'foo',
                'preferred_contact': 'email',
                'gender': 'notachoice',
            }),
            meta={'csrf': False},
        )
        assert form.validate() is False

    def test_validate_contact_phone_no_number(self, person):
        form = ProfileForm(
            formdata=MultiDict({
                'name': 'foo',
                'preferred_contact': 'phone',
                'gender': 'Self-described',
            }),
            meta={'csrf': False},
        )
        assert form.validate() is False
        assert len(form.errors['phone_number']) == 1
        assert "You must enter a phone number" in form.errors['phone_number'][0]

    def test_validate_gender_self_describe_no_description(self, person):
        form = ProfileForm(
            formdata=MultiDict({
                'name': 'foo',
                'preferred_contact': 'email',
                'gender': 'Self-described',
            }),
            meta={'csrf': False},
        )
        assert form.validate() is False
        assert len(form.errors['gender']) == 1
        assert "You selected Self-described but didn't self-describe" == form.errors['gender'][0]

    def test_validate_success(self, person):
        form = ProfileForm(
            formdata=MultiDict({
                'name': 'foo',
                'preferred_contact': 'email',
                'gender': 'Self-described',
                'gender_self_describe': 'my-description',
            }),
            meta={'csrf': False},
        )
        assert form.validate() is True

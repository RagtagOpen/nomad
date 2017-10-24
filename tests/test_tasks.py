# -*- coding: utf-8 -*-
"""Test tasks."""

import datetime
from unittest import mock

from click.testing import CliRunner

from app.models import Carpool
from app.email import reminder_tasks

from .factories import CarpoolFactory

class TestReminders:
    def test_email_in_range(self, monkeypatch, db):
        mock_send_email = mock.Mock()
        monkeypatch.setattr(reminder_tasks, 'send_email', mock_send_email)
        carpool = CarpoolFactory(
            leave_time=datetime.datetime.now() + datetime.timedelta(hours=12),
            reminder_email_sent_at=None,
        )
        db.session.add(carpool)
        db.session.commit()
        expected_args = (
            'driver_reminder',
            carpool.driver.email,
            'Your carpool is coming up!',
        )
        expected_kwargs = {'carpool': carpool}
        runner = CliRunner()
        result = runner.invoke(reminder_tasks.enqueue_scheduled_emails, [])
        assert result.exit_code == 0
        mock_send_email.assert_called_once_with(*expected_args, **expected_kwargs)
        assert len(mock_send_email.call_args_list) == 1
        carpool = db.session.query(Carpool).first()
        assert carpool.reminder_email_sent_at is not None

    def test_email_before_range(self, monkeypatch, db):
        mock_send_email = mock.Mock()
        monkeypatch.setattr(reminder_tasks, 'send_email', mock_send_email)
        carpool = CarpoolFactory(
            leave_time=datetime.datetime.now() - datetime.timedelta(hours=12),
            reminder_email_sent_at=None,
        )
        db.session.add(carpool)
        db.session.commit()
        runner = CliRunner()
        result = runner.invoke(reminder_tasks.enqueue_scheduled_emails, [])
        assert result.exit_code == 0
        assert len(mock_send_email.call_args_list) == 0
        carpool = db.session.query(Carpool).first()
        assert carpool.reminder_email_sent_at is None

    def test_email_after_range(self, monkeypatch, db):
        mock_send_email = mock.Mock()
        monkeypatch.setattr(reminder_tasks, 'send_email', mock_send_email)
        carpool = CarpoolFactory(
            leave_time=datetime.datetime.now() + datetime.timedelta(days=12),
            reminder_email_sent_at=None,
        )
        db.session.add(carpool)
        db.session.commit()
        runner = CliRunner()
        result = runner.invoke(reminder_tasks.enqueue_scheduled_emails, [])
        assert result.exit_code == 0
        assert len(mock_send_email.call_args_list) == 0
        carpool = db.session.query(Carpool).first()
        assert carpool.reminder_email_sent_at is None

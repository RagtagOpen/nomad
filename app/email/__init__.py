from contextlib import contextmanager
from flask import current_app, render_template
from flask_mail import Message

from .. import mail


def make_email_message(html_template, text_template, recipient, subject,
                       **kwargs):
    body = render_template(text_template, **kwargs)
    html = render_template(html_template, **kwargs)
    return Message(
        recipients=[recipient], body=body, html=html, subject=subject)


@contextmanager
def catch_and_log_email_exceptions(messages_to_send):
    try:
        yield
    except Exception as exception:
        current_app.logger.critical(
            'Unable to send email.  {}'.format(repr(exception)))
        _log_emails(messages_to_send)


def _log_emails(messages_to_send):
    for message in messages_to_send:
        current_app.logger.info(
            'Message to {} with subject {} and body {}'.format(
                message.recipients[0], message.subject, message.body))


def send_emails(messages_to_send):
    if current_app.config.get('MAIL_LOG_ONLY'):
        current_app.logger.info(
            'Configured to log {} messages without sending.  Messages in the following lines:'.
            format(len(messages_to_send)))
        _log_emails(messages_to_send)
        return

    with mail.connect() as conn:
        for message in messages_to_send:
            try:
                conn.send(message)
            except Exception as exception:
                current_app.logger.error(
                    'Failed to send message to {} with subject {} and body {} Exception: {}'.
                    format(message.recipients[0], message.subject,
                           message.body, repr(exception)))

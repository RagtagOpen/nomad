from flask import current_app, render_template
from flask_mail import Message

from .. import mail, rq


def send_email(template, recipient, subject, **kwargs):
    if current_app.config.get('RQ_ENABLED'):
        # Enqueue the message to send by the RQ worker
        send_email_queued.queue(template, recipient, subject, **kwargs)
    else:
        # Do the work during the request
        send_email_queued(template, recipient, subject, **kwargs)


@rq.job
def send_email_queued(template, recipient, subject, **kwargs):
    message = Message(
        recipients=[recipient],
        body=render_template('email/{}.txt'.format(template), **kwargs),
        html=render_template('email/{}.html'.format(template), **kwargs),
        subject=subject
    )

    if current_app.config.get('MAIL_LOG_ONLY'):
        current_app.logger.info(
            'Email to "%s", subject "%s", body: "%s"',
            message.recipients,
            message.subject,
            message.body,
        )
        return

    with mail.connect() as conn:
        try:
            conn.send(message)
        except Exception:
            current_app.logger.exception(
                'Failed to send message to %s with subject %s and body %s'.
                message.recipients,
                message.subject,
                message.body,
            )

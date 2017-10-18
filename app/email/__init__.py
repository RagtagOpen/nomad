from flask import current_app, render_template
from flask_mail import Message
from werkzeug.local import LocalProxy

from ..models import UuidMixin
from .. import mail, rq


def send_email(template, recipient, subject, **kwargs):
    # Convert database model instances to serializable dicts
    new_kwargs = {}
    for k, v in kwargs.items():
        if isinstance(v, UuidMixin):
            new_kwargs[k] = {
                'clz': type(v).__name__,
                'uuid': v.uuid,
            }
        elif isinstance(v, LocalProxy) and isinstance(v._get_current_object(), UuidMixin):
            new_kwargs[k] = {
                'clz': type(v._get_current_object()).__name__,
                'uuid': v.uuid,
            }
        else:
            new_kwargs[k] = v

    if current_app.config.get('RQ_ENABLED'):
        # Enqueue the message to send by the RQ worker
        send_email_queued.queue(template, recipient, subject, **new_kwargs)
    else:
        # Do the work during the request
        send_email_queued(template, recipient, subject, **new_kwargs)


@rq.job
def send_email_queued(template, recipient, subject, **kwargs):
    import app.models

    new_kwargs = {}
    for k, v in kwargs.items():
        if isinstance(v, dict):
            clz = v.get('clz')
            uuid = v.get('uuid')

            if clz and uuid:
                clz = getattr(app.models, clz)
                obj = clz.first_by_uuid(uuid)
                if not obj:
                    current_app.logger.error(
                        "Could not find %s instance with uuid %s",
                        clz,
                        uuid,
                    )
                    return False
                else:
                    new_kwargs[k] = obj
        else:
            new_kwargs[k] = v

    message = Message(
        recipients=[recipient],
        body=render_template('email/{}.txt'.format(template), **new_kwargs),
        html=render_template('email/{}.html'.format(template), **new_kwargs),
        subject=subject
    )

    current_app.logger.info(
        'Email to "%s", subject "%s", body: "%s"',
        message.recipients,
        message.subject,
        message.body,
    )

    if current_app.config.get('MAIL_LOG_ONLY'):
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

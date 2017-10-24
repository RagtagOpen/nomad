import datetime
import os
from app import create_app, db
from app.models import Carpool
from app.email import send_email

app = create_app(os.environ.get('CARPOOL_ENV', 'default'))


@app.cli.command()
def enqueue_scheduled_emails():
    search_hours = app.config.get('TRIP_REMINDER_HOURS')

    now = datetime.datetime.now()
    future = now + datetime.timedelta(hours=search_hours)

    upcoming_pools = Carpool.query.filter(
        # Departure time is `search_hours` away
        Carpool.leave_time.between(now, future),
        # ..and we haven't sent the reminder yet
        Carpool.reminder_email_sent_at == None
    )

    app.logger.info("Found %s carpools between %s and %s (%s hours)",
                    upcoming_pools.count(),
                    now,
                    future,
                    search_hours)

    for pool in upcoming_pools:
        app.logger.info("Emailing driver %s about carpool %s",
                        pool.driver.uuid,
                        pool.uuid)

        send_email(
            'driver_reminder',
            pool.driver.email,
            'Your carpool is coming up!',
            carpool=pool,
        )

        for rider in pool.riders:
            app.logger.info("Emailing rider %s about carpool %s",
                            rider.uuid,
                            pool.uuid)

            send_email(
                'rider_reminder',
                rider.email,
                'Your carpool is coming up!',
                rider=rider,
                carpool=pool,
            )

        pool.reminder_email_sent_at = datetime.datetime.now()
        db.session.add(pool)
        db.session.commit()

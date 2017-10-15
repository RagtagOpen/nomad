import datetime
from flask import current_app
from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DateTimeField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    InputRequired,
    NumberRange,
)


def time_select_tuples():
    result = []

    for h in range(1, 12):
        result.append((str(h), "{} AM".format(h)))

    result.append(('12', "12 PM"))

    for h in range(1, 12):
        result.append((str(h + 12), "{} PM".format(h)))

    result.append(('0', "12 AM"))

    return result


class DriverForm(FlaskForm):
    destination = SelectField(
        validators=[
            InputRequired("Please select a destination.")
        ]
    )

    departure_name = StringField()
    departure_lat = HiddenField()
    departure_lon = HiddenField()

    departure_date = DateField()
    departure_hour = SelectField(choices=time_select_tuples(), default='9')

    return_date = DateField()
    return_hour = SelectField(choices=time_select_tuples(), default='9')

    vehicle_description = StringField()
    vehicle_capacity = SelectField(choices=[(str(x), x) for x in range(1, 9)])

    notes = TextAreaField()

    def validate(self):
        if not super(DriverForm, self).validate():
            return False

        result = True

        if not (self.departure_lon.data and self.departure_lat.data):
            self.departure_name.errors.append(
                "No location was found. Try a nearby "
                "street intersection or business.")
            result = False

        if not (self.destination.data):
            self.destination.errors.append(
                "Please select a destination.")
            result = False

        self.departure_datetime = datetime.datetime(
            self.departure_date.data.year,
            self.departure_date.data.month,
            self.departure_date.data.day,
            int(self.departure_hour.data)
        )

        self.return_datetime = datetime.datetime(
            self.return_date.data.year,
            self.return_date.data.month,
            self.return_date.data.day,
            int(self.return_hour.data)
        )

        if self.departure_datetime >= self.return_datetime:
            self.departure_date.errors.append(
                "Your return date should be after your departure date.")
            result = False

        if self.return_datetime < datetime.datetime.today():
            self.return_date.errors.append(
                "Your carpool cannot happen in the past.")
            result = False

        delta = self.return_datetime - self.departure_datetime
        max_trip_length = current_app.config.get('TRIP_MAX_LENGTH_DAYS')
        if delta.days > max_trip_length:
            self.return_date.errors.append(
                "Please return within {} days.".format(max_trip_length))
            result = False

        today = datetime.datetime.today()
        max_days_in_future = current_app.config.get('TRIP_MAX_DAYS_IN_FUTURE')
        if (self.departure_datetime - today).days > max_days_in_future:
            self.departure_date.errors.append(
                "You're leaving too far into the future.")
            result = False

        return result


class RiderForm(FlaskForm):
    notes = TextAreaField("Questions / Notes to Driver")
    submit = SubmitField('Request A Seat')


class CancelCarpoolDriverForm(FlaskForm):
    reason = StringField(
        "Reason",
        description="Describe why you're canceling your carpool. "
                    "This will be visible to your riders."
    )
    cancel = SubmitField("Never Mind, Go Back")
    submit = SubmitField("Cancel Your Ride")


class CancelCarpoolRiderForm(FlaskForm):
    reason = StringField(
        "Reason",
        description="Describe why you're canceling your ride request. "
                    "This will be visible to your driver."
    )
    cancel = SubmitField("Nevermind, Go Back")
    submit = SubmitField("Cancel Your Ride")


class DateSearchForm(FlaskForm):
    depart_time = DateTimeField("Depart Time")
    return_time = DateTimeField("Return Time")
    submit = SubmitField('Search')

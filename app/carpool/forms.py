import datetime
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

        departure_datetime = datetime.datetime(
            self.departure_date.data.year,
            self.departure_date.data.month,
            self.departure_date.data.day,
            int(self.departure_hour.data)
        )

        return_datetime = datetime.datetime(
            self.return_date.data.year,
            self.return_date.data.month,
            self.return_date.data.day,
            int(self.return_hour.data)
        )

        if departure_datetime >= return_datetime:
            self.departure_date.errors.append(
                "Your departure date is after your return date.")
            result = False

        if departure_datetime < datetime.datetime.today():
            self.departure_date.errors.append(
                "You cannot leave before today.")
            result = False

        return result


class RiderForm(FlaskForm):
    submit = SubmitField(u'Request A Seat')


class CancelCarpoolDriverForm(FlaskForm):
    reason = StringField(
        "Reason",
        description="Describe why you're canceling your carpool. "
                    "This will be visible to your riders."
    )
    cancel = SubmitField(u"Never Mind, Go Back")
    submit = SubmitField(u"Cancel Your Ride")


class CancelCarpoolRiderForm(FlaskForm):
    reason = StringField(
        "Reason",
        description="Describe why you're canceling your ride request. "
                    "This will be visible to your driver."
    )
    cancel = SubmitField(u"Nevermind, Go Back")
    submit = SubmitField(u"Cancel Your Ride")


class DateSearchForm(FlaskForm):
    depart_time = DateTimeField("Depart Time")
    return_time = DateTimeField("Return Time")
    submit = SubmitField(u'Search')

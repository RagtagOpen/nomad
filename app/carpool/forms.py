from flask_wtf import FlaskForm
from wtforms import (
    DateTimeField,
    HiddenField,
    IntegerField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    InputRequired,
    NumberRange,
)


class DriverForm(FlaskForm):
    car_size = IntegerField(
        "Number of Seats",
        [
            InputRequired("Please provide the number of seats in your car"),
            NumberRange(1, 10),
        ],
        description="Seats available (besides the driver)",
    )
    leaving_from = StringField(
        "Leaving From",
        [
            InputRequired("Where are you leaving from?"),
        ]
    )
    leaving_from_lat = HiddenField()
    leaving_from_lon = HiddenField()
    depart_time = DateTimeField(
        "Depart Time",
        [
            InputRequired("When are you leaving?"),
        ],
        format='%m/%d/%Y %H:%M',
    )
    going_to = StringField(
        "Going To",
        [
            InputRequired("Where are going to?"),
        ]
    )
    going_to_lat = HiddenField()
    going_to_lon = HiddenField()
    return_time = DateTimeField(
        "Return Time",
        [
            InputRequired("When do you plan to return?"),
        ],
        format='%m/%d/%Y %H:%M',
    )
    submit = SubmitField(u'Add Your Ride')

    def validate(self):
        if not super(DriverForm, self).validate():
            return False

        if self.depart_time.data >= self.return_time.data:
            self.depart_time.errors.append(
                "Departure time must be before return time")
            return False

        return True


class RiderForm(FlaskForm):
    gender = StringField(
        "Gender",
        [
            InputRequired("Please enter your gender"),
        ]
    )
    submit = SubmitField(u'Request A Seat')


class CancelCarpoolDriverForm(FlaskForm):
    reason = StringField(
        "Reason",
        description="Describe why you're canceling your carpool. "
                    "This will be visible to your riders."
    )
    cancel = SubmitField(u"Nevermind, Go Back")
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

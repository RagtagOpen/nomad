from flask_wtf import FlaskForm
from wtforms import (
    DateTimeField,
    HiddenField,
    IntegerField,
    SelectField,
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
    going_to_list = SelectField(
        "Going To",
        [
            InputRequired("Where are going to?"),
        ],
        coerce=int,
    )
    going_to_id = HiddenField()
    going_to_text = StringField()
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

        result = True

        if not (self.leaving_from_lon.data and self.leaving_from_lat.data):
            self.leaving_from.errors.append(
                "No location was found. Try a nearby "
                "street intersection or business.")
            result = False

        if not (self.going_to_lon.data and self.going_to_lat.data):
            self.going_to_list.errors.append(
                "No location was found. Try a nearby "
                "street intersection or business.")
            result = False

        if self.depart_time.data >= self.return_time.data:
            self.depart_time.errors.append(
                "Departure time must be before return time")
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

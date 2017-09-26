from flask_wtf import FlaskForm
from wtforms import (
    HiddenField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    InputRequired,
)


class DestinationForm(FlaskForm):
    name = StringField(
        "Name",
        [
            InputRequired("Please give this destination a name"),
        ]
    )
    address = StringField(
        "Address",
        [
            InputRequired("An address is required"),
        ]
    )
    destination_lat = HiddenField()
    destination_lon = HiddenField()
    submit = SubmitField(u'Add The Destination')


class DeleteDestinationForm(FlaskForm):
    cancel = SubmitField("Nevermind, Go Back")
    submit = SubmitField("Delete The Destination")


class ProfilePurgeForm(FlaskForm):
    cancel = SubmitField("Nevermind, Go Back")
    submit = SubmitField("Permanently Delete Their Profile")

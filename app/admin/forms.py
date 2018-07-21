from flask_wtf import FlaskForm
from wtforms import (
    HiddenField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    InputRequired,
    Length,
)


class DestinationForm(FlaskForm):
    name = StringField(
        "Name",
        [
            InputRequired("Please give this destination a name"),
            Length(3, 80, "Please enter a name between "
                          "3 and 80 characters long"),
        ]
    )
    address = StringField(
        "Address",
        [
            InputRequired("An address is required"),
            Length(3, 300, "Please enter an address between "
                           "3 and 300 characters long"),
        ]
    )
    destination_lat = HiddenField()
    destination_lon = HiddenField()
    submit = SubmitField()

    def validate(self):
        if not super(DestinationForm, self).validate():
            return False

        result = True

        if not (self.destination_lon.data and self.destination_lat.data):
            self.address.errors.append(
                "No location was found. Try a nearby "
                "street intersection or business.")
            result = False

        return result


class DeleteDestinationForm(FlaskForm):
    cancel = SubmitField("Nevermind, Go Back")
    submit = SubmitField("Delete The Destination")


class ProfilePurgeForm(FlaskForm):
    cancel = SubmitField("Nevermind, Go Back")
    submit = SubmitField("Permanently Delete Their Profile")


class CancelCarpoolAdminForm(FlaskForm):
    reason = StringField(
        "Reason",
        description="Describe why you're canceling this carpool. "
                    "This will be visible to allriders."
    )
    cancel = SubmitField("Never Mind, Go Back")
    submit = SubmitField("Cancel This Ride")

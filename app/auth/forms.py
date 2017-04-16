from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
)
from wtforms.validators import (
    InputRequired,
)


class ProfileForm(FlaskForm):
    name = StringField(
        "Name",
        [
            InputRequired("Please enter your name"),
        ]
    )
    submit = SubmitField(u'Update Your Profile')

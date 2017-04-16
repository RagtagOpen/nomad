from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
)
from wtforms.validators import (
    Email,
    InputRequired,
    Length,
    Regexp,
)


class ProfileForm(FlaskForm):
    name = StringField(
        "Name",
        [
            InputRequired("Please enter your name"),
        ]
    )
    email = StringField(
        "Email",
        [
            InputRequired("Please enter your email"),
            Email("Please enter a valid email"),
        ]
    )
    phone_number = StringField(
        "Phone",
        [
            Regexp('\d?-?(\d{3})-?(\d{3})-?(\d{4})', message="Enter a phone number like: 415-867-5309"),
        ]
    )
    gender = StringField(
        "Gender",
    )
    submit = SubmitField(u'Update Your Profile')

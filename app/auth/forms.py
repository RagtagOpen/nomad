from flask_wtf import FlaskForm
from wtforms import (
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    Email,
    InputRequired,
    Optional,
    Regexp,
)
from ..models import Person


class ProfileDeleteForm(FlaskForm):
    name = StringField("Your Name")
    submit = SubmitField('Permanently Delete Your Profile')


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
            Optional(),
            Regexp('\d?-?(\d{3})-?(\d{3})-?(\d{4})',
                   message="Enter a phone number like: 415-867-5309"),
        ]
    )
    preferred_contact = SelectField(
        "Preferred Contact Method",
        [
            InputRequired("Please select a preferred contact method"),
        ],
        choices=zip(Person.CONTACT_METHODS, Person.CONTACT_METHODS),
    )
    gender = StringField(
        "Gender",
        [
            Optional(),
        ]
    )
    submit = SubmitField(u'Update Your Profile')

    def validate(self):
        if not super(ProfileForm, self).validate():
            return False

        if self.preferred_contact.data in (
                Person.CONTACT_CALL, Person.CONTACT_TEXT) \
                and not self.phone_number.data:
            self.phone_number.errors.append(
                "You must enter a phone number if you select call or text "
                "as your preferred method of contact")
            return False

        elif self.preferred_contact.data == Person.CONTACT_EMAIL \
                and not self.email.data:
            self.email.errors.append(
                "You must enter an email if you select email "
                "as your preferred method of contact")
            return False

        return True

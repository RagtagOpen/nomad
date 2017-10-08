from flask_wtf import FlaskForm
from wtforms.fields.html5 import (
    EmailField,
    TelField,
)
from wtforms import (
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    Email,
    InputRequired,
    Length,
    Optional,
    Regexp,
)


class ProfileDeleteForm(FlaskForm):
    name = StringField("Your Name")
    submit = SubmitField('Permanently Delete Your Profile')


class ProfileForm(FlaskForm):
    name = StringField(
        "Name",
        [
            InputRequired("Please enter your name"),
            Length(3, 80,
                   "Please enter a name between 3 and 80 characters long"),
        ]
    )
    email = EmailField(
        "Email",
        [
            InputRequired("Please enter your email"),
            Email("Please enter a valid email"),
        ]
    )
    phone_number = TelField(
        "Phone",
        [
            Optional(),
            Regexp('^\d?-?(\d{3})-?(\d{3})-?(\d{4})$',
                   message="Enter a phone number like: 415-867-5309"),
        ]
    )
    preferred_contact = SelectField(
        "Preferred Contact Method",
        [
            InputRequired("Please select a preferred contact method"),
        ],
        choices=[
            ("", "Select one..."),
            ("email", "Email"),
            ("phone", "Phone"),
            ("text", "Text"),
        ],
    )
    gender = SelectField(
        "Gender",
        [
            InputRequired("Please select a gender"),
        ],
        choices=[
            ("", "Select one..."),
            ("Female", "Female"),
            ("Male", "Male"),
            ("Non-binary / third gender", "Non-binary / third gender"),
            ("self-describe", "Prefer to self-describe"),
            ("Prefer not to say", "Prefer not to say"),
        ]
    )
    gender_self_describe = StringField(
        "Gender",
        [
            Optional(),
            Length(3, 80,
                   "Please enter a name between 3 and 80 characters long"),
        ]
    )
    submit = SubmitField(u'Update Your Profile')

    def validate(self):
        result = True
        if not super(ProfileForm, self).validate():
            result = False

        if self.name.data and not self.name.data.strip():
            self.name.errors.append(
                "Please enter your name")
            result = False

        if self.preferred_contact.data in ('call', 'text') \
                and not self.phone_number.data:
            self.phone_number.errors.append(
                "You must enter a phone number if you select call or text "
                "as your preferred method of contact")
            result = False

        elif self.preferred_contact.data == 'email' \
                and not self.email.data:
            self.email.errors.append(
                "You must enter an email if you select email "
                "as your preferred method of contact")
            result = False

        if self.gender.data == 'self-describe' \
                and not self.gender_self_describe.data:
            self.gender.errors.append(
                "You selected self-describe but didn't self-describe")
            result = False

        return result

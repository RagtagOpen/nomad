from flask_wtf import FlaskForm
from wtforms.fields.html5 import (
    TelField,
)
from wtforms import (
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
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
        "Gender"
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

        if self.preferred_contact.data in ('phone', 'text') \
                and not self.phone_number.data:
            self.phone_number.errors.append(
                "You must enter a phone number if you select phone or text "
                "as your preferred method of contact")
            result = False

        if self.gender.data == 'self-describe' \
                and not self.gender_self_describe.data:
            self.gender.errors.append(
                "You selected self-describe but didn't self-describe")
            result = False

        if self.gender.data == 'self-describe' \
                and self.gender_self_describe.data \
                and len(self.gender_self_describe.data) > 80:
            self.gender.errors.append(
                "Please self-describe in less than 80 characters")
            result = False

        return result

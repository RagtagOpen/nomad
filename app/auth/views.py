from flask import (
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from urlparse import urlparse, urljoin
from . import auth_bp
from .forms import ProfileForm
from .oauth import OAuthSignIn
from .. import db
from ..models import Person


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


def get_redirect_target():
    for target in request.values.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target


@auth_bp.route('/login')
def login():
    next_url = request.args.get('next')
    if next_url and is_safe_url(next_url):
        session['next'] = next_url

    return render_template(
        'login.html',
    )


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('carpool.index'))


@auth_bp.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('carpool.index'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@auth_bp.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('carpool.index'))

    oauth = OAuthSignIn.get_provider(provider)
    social_id, username, email = oauth.callback()

    if social_id is None:
        flash("For some reason, we couldn't log you in. "
              "Please contact us!", 'error')
        return redirect(url_for('carpool.index'))

    user = Person.query.filter_by(social_id=social_id).first()
    if not user:
        user = Person(social_id=social_id, name=username, email=email)
        db.session.add(user)
        db.session.commit()

    login_user(user, True)

    if not user.name:
        flash("Thanks for logging in! Please update your profile.", 'success')
        next_url = url_for('auth.profile')
    else:
        next_url = session.pop('next', None) or url_for('carpool.index')

    return redirect(next_url)


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    profile_form = ProfileForm(
        name=current_user.name,
        gender=current_user.gender,
        email=current_user.email,
        phone_number=current_user.phone_number,
        preferred_contact=current_user.preferred_contact_method,
    )

    # Only tack on the 'choose' thing if they haven't chosen one yet
    if not current_user.preferred_contact_method \
            and not profile_form.preferred_contact.choices[0][0]:
        profile_form.preferred_contact.choices.insert(0, ('', 'choose one'))

    if profile_form.validate_on_submit():
        current_user.name = profile_form.name.data
        current_user.gender = profile_form.gender.data
        current_user.email = profile_form.email.data
        current_user.phone_number = profile_form.phone_number.data
        current_user.preferred_contact_method = \
            profile_form.preferred_contact.data
        db.session.add(current_user)
        db.session.commit()

        flash("You updated your profile.", 'success')

        # If they came here from logging in, redirect them to
        # where they were headed after login.
        next_url = session.pop('next', None) or url_for('auth.profile')

        return redirect(next_url)

    return render_template('profile.html', form=profile_form)


@auth_bp.route('/privacy.html')
def privacy():
    return render_template('privacy.html')

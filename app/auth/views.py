from flask import (current_app, flash, redirect, render_template, request,
                   session, url_for)
from flask_login import current_user, login_required, login_user, logout_user

from six.moves.urllib.parse import urljoin, urlparse

from . import auth_bp
from .. import db, sentry
from ..carpool.views import (cancel_carpool,
                             email_driver_rider_cancelled_request)
from ..models import Person
from .forms import ProfileDeleteForm, ProfileForm
from .oauth import OAuthSignIn


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
    session['login-referrer'] = request.referrer
    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['POST'])
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

    social_id = username = email = None
    try:
        oauth = OAuthSignIn.get_provider(provider)
        social_id, username, email = oauth.callback()
    except:
        current_app.logger.exception("Couldn't log in a user for some reason")
        sentry.captureException()

    if email is None:
        flash("For some reason, we couldn't log you in. "
              "Please contact us!", 'error')
        current_app.logger.warn(
            "Provider %s didn't give email for social id %s, username %s",
            provider,
            social_id,
            username,
        )
        return redirect(url_for('carpool.index'))

    next_url = None

    user = Person.query.filter_by(email=email).first()
    if not user:
        user = Person(social_id=social_id, name=username, email=email)
        db.session.add(user)
        db.session.commit()

        flash("Thanks for logging in! Please update your profile.", 'success')
        # Go to the profile now...
        next_url = url_for('auth.profile')
        # ...and after they update their profile, go to the page that referred them here
        login_referrer = session.pop('login-referrer', None)
        if login_referrer:
            session['next'] = login_referrer

    elif user and user.social_id != social_id:
        # Prevent a user from logging in if they log in with a social account
        # that has an email already added to the system. They should log in with
        # the original social account.
        flash("You've already logged in with another social media account. "
              "Please use that one to log in.", 'error')
        current_app.logger.warn(
            "User %s logged in with a different social provider "
            "(%s) that had a matching email",
            user.id,
            provider,
        )
        return redirect(url_for('auth.login'))

    if user.has_roles('blocked'):
        session.pop('next', None)
        flash("There was a problem logging you in.", 'error')
        current_app.logger.warn("Prevented blocked user %s from logging in",
                                user.id)
        return redirect(url_for('auth.login'))

    login_user(user, True)

    next_url = (next_url or
                session.pop('next', None) or
                url_for('carpool.index'))

    return redirect(next_url)


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    profile_form = ProfileForm(
        name=current_user.name,
        gender=current_user.gender,
        gender_self_describe=current_user.gender_self_describe,
        phone_number=current_user.phone_number,
        preferred_contact=current_user.preferred_contact_method,
    )

    if profile_form.validate_on_submit():
        current_user.name = profile_form.name.data.strip()
        current_user.gender = profile_form.gender.data
        current_user.gender_self_describe = \
            profile_form.gender_self_describe.data.strip()
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
    elif request.method == 'POST':
        flash("We couldn't save your profile changes. See below for the errors.", 'error')

    return render_template('profiles/show.html', form=profile_form)


@auth_bp.route('/profile/delete', methods=['GET', 'POST'])
@login_required
def profile_delete():
    profile_form = ProfileDeleteForm()

    if profile_form.validate_on_submit():
        if profile_form.name.data != current_user.name:
            flash("The text you entered did not match your name.", 'error')
            return redirect(url_for('auth.profile'))

        try:
            # Delete the ride requests for this user
            for req in current_user.get_ride_requests_query():
                current_app.logger.info("Deleting user %s's request %s",
                                        current_user.id, req.id)
                email_driver_rider_cancelled_request(req, req.carpool,
                                                     current_user)
                db.session.delete(req)

            # Delete the carpools for this user
            for pool in current_user.get_driving_carpools():
                current_app.logger.info("Deleting user %s's pool %s",
                                        current_user.id, pool.id)
                cancel_carpool(pool)
                db.session.delete(pool)

            # Delete the user's account
            current_app.logger.info("Deleting user %s", current_user.id)
            user = Person.query.get(current_user.id)
            db.session.delete(user)
            db.session.commit()

            logout_user()
        except:
            db.session.rollback()
            current_app.logger.exception("Problem deleting user account")
            flash("There was a problem deleting your profile. "
                  "Try again or contact us.", 'error')
            return redirect(url_for('auth.profile'))

        flash("You deleted your profile.", 'success')

        return redirect(url_for('carpool.index'))

    return render_template('profiles/delete.html', form=profile_form)


@auth_bp.route('/terms.html')
def terms():
    return render_template('auth/terms.html')

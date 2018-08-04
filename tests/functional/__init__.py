from app.auth.oauth import OAuthSignIn
from flask import request

# A Mock OAuth Provider. Allows for users to be logged in
class MockSignIn(OAuthSignIn):
    def __init__(self):
        self.provider_name = 'mock'

    def authorize(self):
        pass

    def callback(self):
        return (
            request.args.get('id'),
            request.args.get('name'),
            request.args.get('email'),
        )

def login(testapp, social_id, user_name, user_email):
    return testapp.get('/callback/mock', params=dict(id=social_id, name=user_name, email=user_email))

def login_person(testapp, person, follow=True):
    l = login(testapp, person.social_id, person.name, person.email)
    if(follow):
        return l.follow()
    return l

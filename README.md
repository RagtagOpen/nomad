# Nomad

[![Build Status](https://travis-ci.org/RagtagOpen/nomad.svg?branch=master)](https://travis-ci.org/RagtagOpen/nomad)

## Getting Started

1.  Check out the code

    ```
    git clone git@github.com:RagtagOpen/nomad.git
    ```

1.  Go into the checked out repository

    ```bash
    cd nomad
    ```

1.  Local Variables

    Create a file for your local environment variables. This file should be called `.env` and live at the root of the nomad project directory.

    ```bash
    touch .env
    echo FLASK_APP=wsgi.py >> .env
    echo FLASK_DEBUG=1 >> .env
    ```
1.  Add a `SECRET_KEY` to your `.env`. The value for `SECRET_KEY` can be any value for the purposes of local development.

    ```bash
     echo SECRET_KEY=your_secret_key >> .env
    ```

1.  (Optional) Get a Google Maps Api Key

    In order to run the search frontend you will need an API key for Google maps. You can get one [here](https://developers.google.com/maps/documentation/javascript/get-api-key).
    On the "Enable Google Maps Platform" page choose "Maps" as the product.
    ![Enable Google Maps Platform dialog](https://s3.amazonaws.com/assets.ragtag.tech/examples/Screenshot%202018-07-16%2015.30.49.png)
    Then set the key as a variable in your `.env` file.

    ```bash
    echo GOOGLE_MAPS_API_KEY=YOUR_KEY_HERE >> .env
    ```

1.  (Optional) Configure Google Sign-In
    In order to test Google authentication you'll need to create a [Console Project](https://developers.google.com/identity/sign-in/web/devconsole-project).  
    For "Where are you calling from?" choose "Web server".  
    For "Authorized redirect URIs" enter http://localhost:5000/callback/google.  
    After creating credentials you'll get an OAuth Client ID and Client Secret.

    ```bash
    echo GOOGLE_CLIENT_ID=YOUR_CLIENT_ID >> .env
    echo GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET >> .env
    ```


1.  Configure Email Send
    In order for the app to send email, you'll need to add details about what mail server it should use. For testing, you can use a Mailgun or Gmail account. Add those details to the .env file, too!

```bash
echo MAIL_SERVER=smtp.mailgun.org >> .env
echo MAIL_PORT=465 >> .env
echo MAIL_USE_SSL=1 >> .env
echo MAIL_USERNAME=your_username >> .env
echo MAIL_PASSWORD=your_password >> .env
```

If you want to test emails without actually sending them, you can use [MailDev](http://danfarrelly.nyc/MailDev/) with Docker and the following `.env` configuration:

```bash
echo MAIL_SERVER=fakesmtp >> .env
echo MAIL_PORT=25 >> .env
echo MAIL_USE_SSL=0 >> .env
```

With that setup, you can run `docker-compose up nomad fakesmtp` and view emails at [http://localhost:8081/](http://localhost:8081/).

## Running with Docker Compose

You can get up and running with Docker and [Docker Compose](https://docs.docker.com/compose/overview/).
This will allow you to get up and running quickly while installing a smaller set of dependencies to your computer.

1.  [Install Docker](https://www.docker.com/community-edition#/download)

    This will install Docker and Docker Compose. That should be everything you need.

1.  Build the project

    This will build the Docker images that you can use for local development

    ```bash
    # Make sure you're at the root of the nomad project
    # Build the images. This will likely take a few minutes
    # the first time as it needs to download a few images from the Docker registry
    docker-compose build
    ```

1.  Run the project

    This will set up your database, run migrations, and start the application server for you.

    ```bash
    docker-compose up nomad nomad_worker
    ```

1.  Browse to http://127.0.0.1:5000/ in your browser to check it out.

1.  (Optional) Taking more direct control

    If you actually want to drop into a bash prompt in the nomad container you can execute to following command.

    ```bash
    docker-compose run --service-ports nomad bash
    ```

### Misc. notes on developing Nomad in Docker

#### On requirements

If `Pipfile` changes, a `docker-compose build` will reinstall all Python dependencies

#### Accessing the DB

To connect to the DB in docker, run:

```
docker-compose run --service-ports nomad "psql postgresql://nomad:nomad@db/nomad"
```

#### Setting environment variables

`.env` does not get directly `source`'d to the application context; rather, it's used to populate [`docker-compose.yml`](https://github.com/RagtagOpen/nomad/blob/master/docker-compose.yml), which can then be used to set environment variables in the applicaiton context. Therefore, if you add an environment variable in `.env` that you want the app to be able to access, you must also add it in the `environment` block of [`docker-compose.yml`](https://github.com/RagtagOpen/nomad/blob/master/docker-compose.yml).

## Running on Localhost

1.  Install [`pipenv`](https://docs.pipenv.org/#install-pipenv-today)

    ```bash
    brew install pipenv
    ```

    or

    ```bash
    pip install pipenv
    ```

1.  Install the database. The app requires PostgreSQL and PostGIS. [This guide](http://www.postgresguide.com/setup/install.html) describes how to get PostgreSQL running on your computer.

    When you have PostgreSQL installed, you need to create a database for the data to go. Use the `psql` command to connect to your PostgreSQL instance:

    ```bash
    psql
    # psql (9.6.1, server 9.5.4)
    # Type "help" for help.
    ```

    Create the database and add the PostGIS extension:

    ```bash
    create database carpools;
    # CREATE DATABASE
    \connect carpools
    # psql (9.6.1, server 9.5.4)
    # You are now connected to database "carpools" as user "iandees".
    create extension postgis;
    # CREATE EXTENSION
    \quit
    ```

1.  Install the Python dependencies.

    ```bash
    pipenv install
    pipenv shell
    ```

1.  Set up the database

    ```bash
    source .env
    flask db upgrade
    ```

1.  Run the Flask application

    ```bash
    source .env
    flask run
    ```

1.  Browse to http://127.0.0.1:5000/ in your browser to check it out.

## Adding the first admin user

Once you have the app running with Docker or locally, you need to add your first admin user.

1.  With the app running, visit the login page in your browser and login with Facebook or Google.

1.  In a console, bring up a Flask shell:

    If you used Docker:

    ```
    docker-compose run --service-ports nomad flask shell
    ```

    If you are running the app locally:

    ```
    # Make sure you've activated your virtual environment
    source venv/bin/activate
    # Run the flask shell
    source .env
    flask shell
    ```

1.  Add an admin `Role` to your single `Person` instance:

    ```
    from app.models import Role, Person
    from app import db
    r = Role(name='admin', description='Administrator')
    db.session.add(r)
    p = Person.query.first()
    p.roles.append(r)
    db.session.commit()
    ```

1.  Visit `http://127.0.0.1:5000/admin` to verify your account now has the appropriate role.

## Running tests

Using Docker:

    ```
    docker-compose run nomad pytest
    ```

Locally:

    ```
    pytest
    ```

## Branding

Organizations using Nomad need to set these environment variables:

  - `BRANDING_ORG_NAME` - organization name; default "Ragtag"
  - `BRANDING_ORG_SITE_NAME` - site name (not full URL), default "ragtag.org"
  - `BRANDING_LIABILITY_URL` - URL to organizer liability statement (required)
  - `BRANDING_EMAIL_SIGNATURE` - default "The Nomad team"
  - `BRANDING_SUPPORT_EMAIL` - default `support@ragtag.org`

These environment variables have reasonable defaults; setting these is optional:

  - `BRANDING_CSS_URL` - URL to CSS with skin-specific overrides; default is no overrides
  - `BRANDING_HEADLINE_1` - default "Carpool to canvass in battleground districts near you"
  - `BRANDING_HEADLINE_2` - default "Find other volunteers near you and join a carpool."
  - `BRANDING_PRIVACY_URL` - default `/terms.html`; the default [terms.html](app/templates/auth/terms.html) uses values of `BRANDING_ORG_NAME`, `BRANDING_ORG_SITE_NAME`, and `BRANDING_SUPPORT_EMAIL`

### sample Swing Left branding

to use sample sample config for Swing Left locally:

    cat branding/swing-left >> .env

sample branding config values: [branding/swing-left](branding/swing-left)

sample CSS overrides: [static/css/swing-left.css](app/static/css/swing-left.css)

restart app to reload config from `.env`

### branding QA

  - `BRANDING_ORG_NAME` in [terms.html](app/templates/auth/terms.html) (ie "Ragtag Nomad Privacy Policy")
  - `BRANDING_ORG_SITE_NAME` in [terms.html](app/templates/auth/terms.html) ie "nomad.ragtag.org, the "Site""
  - `BRANDING_SUPPORT_EMAIL` in [terms.html](app/templates/auth/terms.html) ie "email support@ragtag.org"
  - `BRANDING_LIABILITY_URL` in email templates: [driver_reminder](app/templates/email/driver_reminder.html), [ride_approved.html](app/templates/email/ride_approved.html)
  - `BRANDING_EMAIL_SIGNATURE` in all [email templates](app/templates/email)
  - logo on home page, defined in CSS referenced by `BRANDING_CSS_URL`
  - `BRANDING_HEADLINE_1` and `BRANDING_HEADLINE_1` on home page, below "SHARE YOUR RIDE"
  - `BRANDING_PRIVACY_URL` privacy policy links on [login](app/templates/auth/login.html) and [mobile and desktop nav](app/templates/_template.html)

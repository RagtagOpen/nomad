# Nomad

[![Build Status](https://travis-ci.org/RagtagOpen/nomad.svg?branch=master)](https://travis-ci.org/RagtagOpen/nomad)

## Getting Started
1. Check out the code

    ```
    git clone git@github.com:RagtagOpen/nomad.git
    ```

1. Go into the checked out repository

    ```bash
    cd nomad
    ```

1. Local Variables

    Create a file for your local environment variables. This file should be called `.env` and live at the root of the nomad project directory.

    ```bash
    touch .env
    echo FLASK_APP=wsgi.py >> .env
    echo FLASK_DEBUG=1 >> .env
    ```

1. (Optional) Get a Google Maps Api Key

    In order to run the search frontend you will need an API key for Google maps. You can get one [here](https://developers.google.com/maps/documentation/javascript/get-api-key).
    Then set the key as a variable in your `.env` file.

    ```bash
    echo GOOGLE_MAPS_API_KEY="YOUR_KEY_HERE" >> .env
    ```

1. (Optional) Configure Google Sign-In
    In order to test Google authentication you'll need to create a [Console Project](https://developers.google.com/identity/sign-in/web/devconsole-project).
    After creating credentials you'll get an OAuth Client ID and Client Secret. These need to go into your .env file as well.

    ```bash
    echo GOOGLE_CLIENT_ID="YOUR_CLIENT_ID" >> .env
    echo GOOGLE_CLIENT_SECRET="YOUR_CLIENT_SECRET" >> .env
    ```

1. Configure Email Send
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

1. [Install Docker](https://www.docker.com/community-edition#/download)

    This will install Docker and Docker Compose. That should be everything you need.

1. Build the project

    This will build the Docker images that you can use for local development

    ```bash
    # Make sure you're at the root of the nomad project
    # Build the images. This will likely take a few minutes
    # the first time as it needs to download a few images from the Docker registry
    docker-compose build
    ```

1. Run the project

    This will set up your database, run migrations, and start the application server for you.

    ```bash
    docker-compose up nomad nomad_worker
    ```

1. Browse to http://127.0.0.1:5000/ in your browser to check it out.

1. (Optional) Taking more direct control

    If you actually want to drop into a bash prompt in the nomad container you can execute to following command.

    ```bash
    docker-compose run --service-ports nomad bash
    ```

### Misc. notes on developing Nomad in Docker

#### On requirements

If `requirements.txt` changes, a `docker-compose build` will reinstall all Python dependencies

#### Accessing the DB

To connect to the DB in docker, run:
```
docker-compose run --service-ports nomad "psql postgresql://nomad:nomad@db/nomad"
```

#### Setting environment variables
`.env` does not get directly `source`'d to the application context; rather, it's used to populate [`docker-compose.yml`](https://github.com/RagtagOpen/nomad/blob/master/docker-compose.yml), which can then be used to set environment variables in the applicaiton context. Therefore, if you add an environment variable in `.env` that you want the app to be able to access, you must also add it in the `environment` block of [`docker-compose.yml`](https://github.com/RagtagOpen/nomad/blob/master/docker-compose.yml).

## Running on Localhost

1. Set up a virtual environment

   ```bash
   virtualenv venv
   source venv/bin/activate
   ```

1. Install the database. The app requires PostgreSQL and PostGIS. [This guide](http://www.postgresguide.com/setup/install.html) describes how to get PostgreSQL running on your computer.

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

1. Install the Python dependencies.

   ```bash
   pip install -r requirements.txt
   ```

1. Set up the database

   ```bash
   source .env
   flask db upgrade
   ```

1. Run the Flask application

   ```bash
   source .env
   flask run
   ```

1. Browse to http://127.0.0.1:5000/ in your browser to check it out.

## Adding the first admin user

Once you have the app running with Docker or locally, you need to add your first admin user.

1. With the app running, visit the login page in your browser and login with Facebook or Google.

1. In a console, bring up a Flask shell:

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

1. Add an admin `Role` to your single `Person` instance:

    ```
    from app.models import Role, Person
    from app import db
    r = Role(name='admin', description='Administrator')
    db.session.add(r)
    p = Person.query.first()
    p.roles.append(r)
    db.session.commit()
    ```

1. Visit `http://127.0.0.1:5000/admin` to verify your account now has the appropriate role.

## Running tests

Using Docker:

    ```
    docker-compose run nomad pytest
    ```

Locally:

    ```
    pytest
    ```

# Nomad

## Gettng Started
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
    After going through the project creation step you'll have an auto-generated project ID. This needs to go in your `.env` file.

    ```bash
    echo GOOGLE_APP_ID="YOUR_APP_ID" >> .env
    ```

    After creating credentials you'll get an OAuth Client ID and Client Secret. These need to go into your .env file as well. 
    
    ```bash
    echo GOOGLE_CLIENT_ID="YOUR_CLIENT_ID" >> .env
    echo GOOGLE_CLIENT_SECRET="YOUR_CLIENT_SECRET" >> .env
    ``` 
     
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
    docker-compose up nomad
    ```
    
1. Browse to http://127.0.0.1:5000/ in your browser to check it out.

1. (Optional) Taking more direct control

    If you actually want to drop into a bash prompt in the nomad container you can execute to following command.

    ```bash
    docker-compose run --service-ports nomad bash
    ```

### Note 

If `requirements.txt` changes a `docker-compose build` will reinstall all Python dependencies

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

# carpools

## Running

1. Check out the code

   ```
   git clone git@github.com:iandees/carpools.git
   ```

1. Go in to the checked out repository

   ```
   cd carpools
   ```

1. Set up a virtual environment

   ```
   virtualenv venv
   source venv/bin/activate
   ```

1. Install the database. The app requires PostgreSQL and PostGIS. [This guide](http://www.postgresguide.com/setup/install.html) describes how to get PostgreSQL running on your computer.

   When you have PostgreSQL installed, you need to create a database for the data to go. Use the `psql` command to connect to your PostgreSQL instance:

   ```
   $ psql
   psql (9.6.1, server 9.5.4)
   Type "help" for help.

   iandees=#
   ```

   Create the database and add the PostGIS extension:
   ```
   iandees=# create database carpools;
   CREATE DATABASE
   iandees=# \connect carpools
   psql (9.6.1, server 9.5.4)
   You are now connected to database "carpools" as user "iandees".
   carpools=# create extension postgis;
   CREATE EXTENSION
   carpools=# \quit
   ```

1. Install the Python dependencies.

   ```
   pip install -r requirements.txt
   ```

1. Set up the Flask framework configuration

   ```
   export FLASK_APP=app.py
   export FLASK_DEBUG=1
   ```

1. Set up the database

   ```
   flask db upgrade
   ```

1. Run the Flask application

   ```
   flask run
   ```

1. Browse to http://127.0.0.1:5000/ in your browser to check it out.

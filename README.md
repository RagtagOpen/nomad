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

1. Install the dependencies

   ```
   pip install -r requirements-dev.txt
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

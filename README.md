# carpools

## Running

```
# Check out the code
git clone git@github.com:iandees/carpools.git
# Go in to the checked out repository
cd carpools
# Set up a virtual environment
virtualenv venv
source venv/bin/activate
# Install the dependencies
pip install -r requirements.txt
# Set up the Flask framework configuration
export FLASK_APP=app.py
export FLASK_DEBUG=1
# Set up the database
flask db upgrade
# Run the Flask application
flask run
```

Browse to http://127.0.0.1:5000/ in your browser to check it out.

release: env; flask db upgrade
web: gunicorn wsgi:app -b 0.0.0.0:$PORT -w 3

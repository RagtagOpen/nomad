release: psql $DATABASE_URL -q -c "CREATE EXTENSION IF NOT EXISTS postgis"; flask db upgrade
web: gunicorn wsgi:app -b 0.0.0.0:$PORT -w 3
worker: flask rq worker

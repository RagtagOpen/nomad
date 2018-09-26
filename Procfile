release: psql $DATABASE_URL -q -c "CREATE EXTENSION IF NOT EXISTS postgis"; flask db upgrade
web: bin/start-nginx gunicorn wsgi:app -c config/gunicorn.conf -w 3 --enable-stdio-inheritance --log-file -
worker: flask rq worker


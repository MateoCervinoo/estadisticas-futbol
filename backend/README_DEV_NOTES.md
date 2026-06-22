Notes for DB waiting

- The Dockerfile runs `wait-for-db.sh` before launching Uvicorn. This simple script uses psql to check availability.
- Ensure the image has `psql` available; the base image installs `libpq-dev` so python drivers can compile and psql is available in Debian slim images when `postgresql-client` is installed. If psql isn't available, install `postgresql-client`.

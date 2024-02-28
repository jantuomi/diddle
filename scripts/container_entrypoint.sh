#!/bin/sh
set -euxo pipefail

python apply_migrations.py
gunicorn --bind "0.0.0.0:8000" -w 4 app:app

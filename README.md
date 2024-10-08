# diddle

Minimalist scheduling. A mobile friendly, fast, self-hosted Doodle alternative.

## Installation

The Diddle app is a traditional Flask web app that uses SQLite for persistence. User settings are stored in HTTP cookies.

Build a container image with `docker compose` (see `compose.yml`):

    docker compose build

or directly with `docker build`:

    docker build -t diddle:latest .

Deploy the image as you see fit.

You can also run the app without containerization:

    pip install -r requirements.txt # install pip dependencies
    touch .env                      # put your env vars here
    python apply_migrations.py      # prepare the database
    gunicorn --bind "0.0.0.0:8000" -w 4 app:app

## Environment variables

| Variable | Description |
| -------- | ----------- |
| BASE_URL | E.g. `diddle.my-server.net`, used as a prefix in dynamically generated links **(required)** |
| DB_PATH | Path to the SQLite database **(required)** |
| EMAIL_HOST | SMTP host address |
| EMAIL_PORT | SMTP port |
| EMAIL_HOST_USER | SMTP host user |
| EMAIL_HOST_PASSWORD | SMTP host password |
| EMAIL_USE_TLS | Use STARTTLS with SMTP? |
| EMAIL_HEADERS | Additional SMTP headers, format: `header1=foo,header2=bar` |
| EMAIL_MESSAGE_FROM | Email message from address |

`EMAIL_` variables are only required if at least one of them is defined.

## Screenshots

### Front page

![Front page](docs/screenshot_frontpage.png)

### Manage poll page

![Manage poll page](docs/screenshot_manage.png)

### Vote page (table mode)

![Vote page table mode](docs/screenshot_poll_table.png)

### Vote page (list mode)

![Vote page list mode](docs/screenshot_poll_list.png)

## Development

Run Flask in dev mode:

    flask --app app --debug run -p 8000

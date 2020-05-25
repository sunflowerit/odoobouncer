# Nginx extra security layer for Odoo

## Installation

### Install `pipenv`

    sudo pip install pipenv

### Prepare project first time

    python3 -m venv .venv
    pipenv install
    cp .env-template .env
    vi .env  # edit settings
    python generate-secret-code.py
    vi .env  # copy generated code into here

## Usage in debug mode

    pipenv run python nginx-odoo.py

## Usage in production

Install UWSGI:

    sudo apt install uwsgi uwsgi-plugin-python3

Now create a new UWSGI config file:

    [uwsgi]
    for-readline = /home/ubuntu/nginx-odoo/.env
      env = %(_)
    plugins = python3
    virtualenv = /home/ubuntu/nginx-odoo/.venv
    socket = :8888
    chdir = /home/ubuntu/nginx-odoo
    master = true
    file = nginx-odoo.py
    uid = ubuntu
    gid = ubuntu

Now configure NGINX:

TODO: explain how to configure nginx `auth_request` to http://127.0.0.1:8888/


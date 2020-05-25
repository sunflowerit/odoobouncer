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

    auth_request /nginx-odoo-auth;

    location /web/session/logout {
        proxy_pass http://localhost:8888/logout;
        proxy_pass_request_body off;
    }

    location /web/session/destroy {
        proxy_pass http://localhost:8888/logout;
        proxy_pass_request_body off;
    }

    location = /nginx-odoo-auth {
        proxy_pass http://localhost:8888/auth;
        proxy_pass_request_body off;
    }

    location ~ /nginx-odoo-login(.*)$ {
        auth_request off;
        proxy_pass http://localhost:8888$1;
        proxy_redirect     off;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

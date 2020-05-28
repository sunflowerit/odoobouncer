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
    http-socket = :8888
    chdir = /home/ubuntu/nginx-odoo
    master = true
    file = nginx-odoo.py
    uid = ubuntu
    gid = ubuntu

Now configure NGINX by adding this section:

    # === START: Configuration for nginx-odoo ===
    set $nginxodoourl http://127.0.0.1:8888;
    set $odoourl http://127.0.0.1:8069;
    auth_request /nginx-odoo-auth;
    error_page 401 = @error401;
    location @error401 {
        return 302 https://$http_host/nginx-odoo-login/;
    }
    location /web/login {
        return 302 https://$http_host/;
    }
    location = /web/session/authenticate {
        auth_request off;
        proxy_pass $nginxodoourl;
    }
    location = /web/webclient/version_info {
        auth_request off;
        proxy_pass $odoourl;
        proxy_pass_request_headers off;
        proxy_set_header Content-Type application/json;
    }
    location = /web/database/list {
        auth_request off;
        proxy_pass $odoourl;
        proxy_pass_request_headers off;
        proxy_set_header Content-Type application/json;
    }

    location /web/session/logout {
        proxy_pass $nginxodoourl/logout;
        proxy_pass_request_body off;
    }
    location /web/session/destroy {
        proxy_pass $nginxodoourl/logout;
        proxy_pass_request_body off;
    }
    location = /nginx-odoo-auth {
        proxy_pass $nginxodoourl/auth;
        proxy_pass_request_body off;
    }
    location ~ /nginx-odoo-login(.*)$ {
        auth_request off;
        proxy_pass $nginxodoourl$1;
        proxy_redirect     off;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
    # === END: Configuration for nginx-odoo ===

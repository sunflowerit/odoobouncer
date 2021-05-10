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
    auth_request /nginx-odoo-auth;

    error_page 401 = @error401;

    location @error401 {
        return 302 https://$http_host/nginx-odoo-login/;
    }

    location = /web/login {
        return 302 https://$http_host/nginx-odoo-login/;
    }

    location = /web/session/authenticate {
        proxy_pass http://$authentication_provider_address:$authentication_provider_port;
        auth_request off;
    }

    error_page 418 = @pass_directly_to_odoo;
    location = /web/binary/company_logo { return 418; }
    location ~ ^/web/static/(.*).ico$ { return 418; }
    location ~ ^/web/static/(.*).png$ { return 418; }
    location ~ ^/web/static/(.*).css$ { return 418; }
    location ~ ^/web/content/(.*?)/(.*?).css$ { return 418; }
    location ~ ^/web/content/(.*?)/(.*?)/(.*?).css$ { return 418; }
    location ~ ^/mail/tracking/open/(.*?)/(.*?)/blank.gif { return 418; }
    location = /web/database/list { return 418; }
    location = /web/webclient/version_info { return 418; }
    location = /web/reset_password { return 418; }
    location = /web/signup { return 418; }
    location @pass_directly_to_odoo {
        auth_request off;
        proxy_pass http://$web_provider_address:$web_provider_port;
        # ===
        # I had this, so that attackers cannot use this URL as an attack vector
        # to fire stolen session_id's at.
        # But it causes Odoo to come with the Set-Cookie response
        # which starts a new un-2FA'ed session and breaks things.
        # It's either to refuse response headers also, or to forget about it
        # completely.
        # ---
        # proxy_pass_request_headers off;
        # # for /web/webclient/version_info, /web/database/list
        # proxy_set_header Content-Type application/json;
        # # for /web/reset_password
        # proxy_redirect off;
    }

    location = /web/session/logout {
        proxy_pass http://$authentication_provider_address:$authentication_provider_port/logout;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
    }

    location = /web/session/destroy {
        proxy_pass http://$authentication_provider_address:$authentication_provider_port/logout;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
    }

    location = /nginx-odoo-auth {
        proxy_pass http://$authentication_provider_address:$authentication_provider_port/auth;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
    }

    location = /nginx-odoo-login { return 302 /nginx-odoo-login/; }
    location ~ ^/nginx-odoo-login/(.*)$ {
        proxy_pass http://$authentication_provider_address:$authentication_provider_port/$1$is_arg$args;
        proxy_redirect off;
        auth_request off;
    }
    # === END: Configuration for nginx-odoo ===

# Authentication

The bouncer can also be used for authentication.
When logging in on /nginx-odoo-login, add a query string with the key "redirect". The value should be the url to redirect to once the user has logged in.
When redirecting to the given url, the session_id will be added to the end of the url

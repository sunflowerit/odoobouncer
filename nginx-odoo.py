#!/bin/env python
# Copyright 2020 Sunflower IT

import sys
assert sys.version_info.major == 3, 'Requires Python 3.'

import argparse
import base64
import bottle
import configparser
import odoorpc
import os
import pyotp
import signal
import threading

from bottle import request, route, run, static_file, template
from urllib.parse import urlparse


HOTP_SECRET = os.environ.get('FFHOTP_SECRET')
assert(len(HOTP_SECRET) == 16)

user_config_dir = os.path.expanduser("~") + "/.config/nginx-odoo"
user_config = user_config_dir + "/nginx-odoo.ini"


# Load and increase HOTP counter
def update_hotp_counter():
    config_ok = False
    counter = 0
    if os.path.isfile(user_config):
        try:
            config = configparser.ConfigParser()
            config.read(user_config)
            counter = int(config['hotp']['counter'])
            config_ok = True
            # TODO: assert file permissions 600
        except Exception:
            pass

    if not config_ok:
        os.makedirs(user_config_dir, exist_ok=True)
        config = configparser.ConfigParser()
        config.add_section('hotp')
        config['hotp']['counter'] = str(counter)
        with open(user_config, 'w') as f:
            config.write(f)
            # TODO: set file permissions 600

    counter += 1
    config['hotp']['counter'] = str(counter)
    with open(user_config, 'w') as f:
        config.write(f)
    return counter


class OdooAuthHandler():
    
    params =  {
        'host': None,
        'port': None,
    }

    @classmethod
    def set_params(cls, params):
        cls.params = params

    def check_login(self, username, password):
        host = self.params.get('host')
        port = self.params.get('port')
        database = self.params.get('database')
        try:
            odoo = odoorpc.ODOO(host, port=port, protocol='jsonrpc')
            odoo.login(database, username, password)

            hotp = pyotp.HOTP(HOTP_SECRET)
            counter = update_hotp_counter()
            key = hotp.at(counter)
            print('sending out {}: {}'.format(key, counter))

            # TODO: store the numbers somewhere safe, with an expiration date

            # TODO: verify
            #hotp.verify('316439', 1401) # => True
            #hotp.verify('316439', 1402) # => False

            # TODO: check user object for the 'portal flag'
            # TODO: proceed to second factor auth: send out code
            # TODO: now return odoo session id cookie to NGINX
            #       and have our own JWT mechanism for allowing this device from now on
            #       (maybe through oauthlib after all)
            return True
        except odoorpc.error.RPCError:
            return False


# Static Routes (CSS, images)
@route("/static/<filepath:re:.*\.(css|jpg|png)>", method='GET')
def css(filepath):
    return static_file(filepath, root="static")


# Main page: login form
@route('/')
def login():
    return template('login')


# Main page posts to /login
@route('/login', method='POST')
def do_login():
    username = request.forms.get('username')
    password = request.forms.get('password')
    handler = OdooAuthHandler()
    if handler.check_login(username, password):
        return "<p>Your login information was correct.</p>"
    else:
        return bottle.HTTPResponse(
            status=401, body="<p>Login failed.</p>")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""Simple Nginx Odoo authentication helper.""")

    # Group for listen options:
    group = parser.add_argument_group("Listen options")
    group.add_argument('--host',  metavar="hostname",
        default="localhost", help="host to bind (Default: localhost)")
    group.add_argument('-p', '--port', metavar="port", type=int,
        default=8888, help="port to bind (Default: 8888)")

    # Odoo options:
    group = parser.add_argument_group(title="Odoo options")
    group.add_argument('-u', '--url', metavar="URL",
        default="http://localhost:8069",
        help=("Odoo URI to query (Default: http://localhost:8169)"))
    group.add_argument('-d', '--database', metavar="URL",
        default="freshfilter_demo",
        help=("Odoo database to query (Default: freshfilter_demo)"))

    # Parse arguments
    args = parser.parse_args()

    # Increase the HOTP counter
    update_hotp_counter()

    # Discover more about the Odoo instance
    url = urlparse(args.url)
    assert url.scheme == 'http', 'HTTPS not supported'
    odoo_port = url.port
    odoo_host = url.hostname
    odoo_database = args.database
    odoo = odoorpc.ODOO(odoo_host, port=odoo_port)

    auth_params = {
        'host': odoo_host,
        'port': odoo_port,
        'database': odoo_database,
    }
    OdooAuthHandler.set_params(auth_params)

    run(server='paste', host=args.host, port=args.port)

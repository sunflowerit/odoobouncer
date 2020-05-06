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

from bottle import redirect, request, route, run, static_file, template
from urllib.parse import urlparse

from lib.db import DB


HOTP_SECRET = os.environ.get('FFHOTP_SECRET')
assert(len(HOTP_SECRET) == 16)

user_config_dir = os.path.expanduser("~") + "/.config/nginx-odoo"
db_path = user_config_dir + "/database.db"
db = DB(db_path)  # TODO: assert file permissions 600


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
            # TODO: check user object for the 'portal flag'
            return True

            # TODO: is_expired function for counter

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


# Login page
@route('/')
def login_page():
    # TODO: verify session cookie and if yes, return hurray code to nginx
    # TODO: extra protection eg. by IP or browser signature
    return template('login')


# Handle login
@route('/', method='POST')
def do_verify():
    # check if this is first login
    username = request.forms.get('username')
    password = request.forms.get('password')
    if username and password:
        handler = OdooAuthHandler()
        if handler.check_login(username, password):
            hotp = pyotp.HOTP(HOTP_SECRET)
            counter, code = db.next_hotp_id()
            key = hotp.at(counter)
            print('sending out {}: {}'.format(key, counter))
            print('requiring code: {}'.format(code))
            # TODO: send out hotp code by mail
            # TODO: keep a logfile about sent mails
            return template('hotp', counter=counter, code=code)
        else:
            # TODO: show failed password message
            # TODO: brute force protection
            return redirect('/')
            # TODO: do we return 401 here for nginx?
            # return bottle.HTTPResponse(
            #     status=401, body="<p>Login failed.</p>")

    # check HOTP
    counter = request.forms.get('counter')
    code = request.forms.get('code')
    hotp_code = request.forms.get('hotp_code')
    if code and counter and hotp_code:
        hotp = pyotp.HOTP(HOTP_SECRET)
        if hotp.verify(hotp_code, int(counter)) and \
                db.verify_code(counter, code):
            return bottle.HTTPResponse(
                status=200, body="<p>Login successful.</p>")
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

#!/bin/env python
# Copyright 2020 Sunflower IT

# TODO: for extra safety, dont let session_id be Odoo session id,
# but make a new JWT token that includes the Odoo session id, and translate in NGINX.
# TODO: prevent people logging out, but setting session_id again with cookie manager,
# then coming to Odoo login screen and guessing admin password.

import sys
assert sys.version_info.major == 3, 'Requires Python 3.'

import argparse
import base64
import bottle
import configparser
import odoorpc
import os
import pyotp
import re
import smtplib
import signal
import threading

from bottle import \
    redirect, request, response, route, run, static_file, template
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urlparse

from lib.db import DB

# TODO: should this be in __main__ ?

email_regex = re.compile(
    r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$")

# load and check HOTP secret
HOTP_SECRET = os.environ.get('FFHOTP_SECRET')
if not HOTP_SECRET or len(HOTP_SECRET) != 16:
    sys.exit('HOTP secret in .envrc must be 16 characters')

# load and check email settings
SMTP_SERVER = os.environ.get('FFSMTP_SERVER')
SMTP_FROM = os.environ.get('FFSMTP_FROM')
SMTP_TO = os.environ.get('FFSMTP_TO')
if not SMTP_SERVER or not SMTP_FROM:
    sys.exit('SMTP settings not set in .envrc')
s = smtplib.SMTP(SMTP_SERVER)
s.close()

# open database
user_home_dir = os.path.expanduser("~")
user_config_dir = os.path.expanduser("~") + "/.config/nginx-odoo"
Path(user_config_dir).mkdir(parents=True, exist_ok=True)
db_path = user_config_dir + "/database.db"
db = DB(db_path)
os.chmod(db_path, 0o600)
db_perm = os.stat(db_path).st_mode & 0o777
if db_perm != 0o600:
    sys.exit('File permissions of {} must be 600 but are: {:o}'.format(
        db_path, db_perm))
db.cleanup()


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
            data = odoo.json('/web/session/authenticate', {
                'db': database, 'login': username, 'password': password
            })
            result = data.get('result')
            session_id = result.get('session_id')
            if not result.get('uid') or not session_id:
                return False
            # TODO: check user object for the 'portal flag'
            return session_id
        except odoorpc.error.RPCError:
            # TODO: log exception
            return False


# Static Routes (CSS, images)
@route("/static/<filepath:re:.*\.(css|jpg|png)>", method='GET')
def css(filepath):
    return static_file(filepath, root="static")


# Session logout
@route('/logout')
def logout_session():
    session = request.get_cookie('session_id')
    db.remove_session(session)
    return redirect('/')


# Session verification
@route('/auth')
def verify_session():
    session = request.get_cookie('session_id')
    if db.verify_session(session):
        return bottle.HTTPResponse(status=200)
    return bottle.HTTPResponse(status=401)


# Login page
@route('/')
def login_page():
    # TODO: extra protection eg. by IP or browser signature
    return template('login')


def send_mail(username, code):
    # TODO: send to email address of user
    if username == 'admin' and SMTP_TO:
        _to = SMTP_TO
    else:
        _to = username
    if not _to:
        return False
    _to_list = _to.split(',')
    if not all(email_regex.match(t) for t in _to_list):
        return False
    msg = MIMEText("Freshfilter security code: {}".format(code))
    msg['Subject'] = "Freshfilter security code: {}".format(code)
    msg['From'] = SMTP_FROM
    msg['To'] = _to
    s = smtplib.SMTP(SMTP_SERVER)
    s.sendmail(SMTP_FROM, _to_list, msg.as_string())
    s.quit()
    return True


# Handle login
@route('/', method='POST')
def do_verify():

    # handle username/password
    # TODO: CSRF protection
    username = request.forms.get('username')
    password = request.forms.get('password')
    if username and password:
        handler = OdooAuthHandler()
        session_id = handler.check_login(username, password)
        if session_id:
            hotp = pyotp.HOTP(HOTP_SECRET)
            counter, code = db.next_hotp_id(session_id)
            key = hotp.at(counter)
            # TODO: keep a logfile about sent mails
            if not send_mail(username, key):
                # TODO: show failed message
                # https://github.com/polonel/SnackBar
                return redirect('/')
            return template('hotp', counter=counter, code=code)
        else:
            # TODO: show failed password message
            # TODO: brute force protection
            #       (block for X minutes after X attempts)
            return redirect('/')

    # check HOTP
    counter = request.forms.get('counter')
    code = request.forms.get('code')
    hotp_code = request.forms.get('hotp_code')
    if code and counter and hotp_code:
        hotp = pyotp.HOTP(HOTP_SECRET)
        if not hotp.verify(hotp_code, int(counter)):
            return redirect('/')
        session_id = db.verify_code_and_expiry(counter, code)
        if not session_id:
            # TODO: show failed code message
            return redirect('/')
        db.save_session(session_id)
        # TODO: log('Setting session cookie: {}'.format(session_id))
        response.set_cookie("session_id", session_id, path='/')
        return redirect('/')

    return redirect('/')


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
        help=("Odoo URI to query (Default: http://localhost:8069)"))
    group.add_argument('-d', '--database', metavar="URL",
        required=True,
        help=("Odoo database to query (Default: freshfilter_demo)"))

    # Parse arguments
    args = parser.parse_args()

    # Discover more about the Odoo instance
    url = urlparse(args.url)
    assert url.scheme == 'http', 'HTTPS not supported'
    odoo_port = url.port
    odoo_host = url.hostname
    odoo_database = args.database

    try:
        odoo = odoorpc.ODOO(odoo_host, port=odoo_port)
    except Exception:
        sys.exit('Odoo not running at {}'.format(args.url))

    databases = odoo.db.list()
    if odoo_database not in databases:
        sys.exit('Database {} not present at {}'.format(
            odoo_database, args.url))

    auth_params = {
        'host': odoo_host,
        'port': odoo_port,
        'database': odoo_database,
    }
    OdooAuthHandler.set_params(auth_params)

    run(server='paste', host=args.host, port=args.port)

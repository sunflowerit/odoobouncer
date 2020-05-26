#!/bin/env python
# Copyright 2020 Sunflower IT

# TODO: for extra safety, dont let session_id be Odoo session id,
# but make a new JWT token that includes the Odoo session id,
# and translate in NGINX.
# TODO: prevent people logging out, but setting session_id again
# with cookie manager, then coming to Odoo login screen and
# guessing admin password.

import sys
import bottle
import odoorpc
import os
import pyotp
import re
import smtplib

from bottle import \
    redirect, request, response, static_file, template
from email.mime.text import MIMEText
from pathlib import Path

from lib.db import DB
from lib.odooauth import OdooAuthHandler


assert sys.version_info.major == 3, 'Requires Python 3.'

email_regex = re.compile(
    r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$")

# load and check HOTP secret
HOTP_SECRET = os.environ.get('NGINX_ODOO_HOTP_SECRET')
hotp_secret_length = len(HOTP_SECRET) if HOTP_SECRET else 0
if hotp_secret_length != 16:
    sys.exit('HOTP secret in .env must be 16 characters, has {}'.format(
        hotp_secret_length))

# load and check listen settings
# (when running as a developer, from command line instead of with uwsgi)
LISTEN_PORT = os.environ.get('NGINX_ODOO_LISTEN_PORT', 8888)
LISTEN_HOST = os.environ.get('NGINX_ODOO_LISTEN_HOST', 'localhost')

# load and check branding settings
BRANDING = os.environ.get('NGINX_ODOO_BRANDING', '')
BACKGROUNDCOLOR = os.environ.get('NGINX_ODOO_BACKGROUND_COLOR', '')
BUTTONCOLOR = os.environ.get('NGINX_ODOO_BUTTON_COLOR', '')
BUTTONHOVERCOLOR = os.environ.get('NGINX_ODOO_BUTTON_HOVER_COLOR', '')
BUTTONSHADOWCOLOR = os.environ.get('NGINX_ODOO_BUTTON_SHADOW_COLOR', '')

# load and check email settings
SMTP_SERVER = os.environ.get('NGINX_ODOO_SMTP_SERVER')
SMTP_SSL = os.environ.get('NGINX_ODOO_SMTP_SSL')
SMTP_PORT = os.environ.get('NGINX_ODOO_SMTP_PORT', 465 if SMTP_SSL else 25)
SMTP_FROM = os.environ.get('NGINX_ODOO_SMTP_FROM')
SMTP_TO = os.environ.get('NGINX_ODOO_SMTP_TO')
SMTP_USER = os.environ.get('NGINX_ODOO_SMTP_USER')
SMTP_PASS = os.environ.get('NGINX_ODOO_SMTP_PASS')

if not SMTP_SERVER or not SMTP_FROM:
    sys.exit('SMTP settings not set in .env')


def smtp_connect():
    if SMTP_SSL:
        s = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=5)
    else:
        s = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=5)
    return s


def smtp_login(s):
    if SMTP_USER:
        s.login(SMTP_USER, SMTP_PASS)
    return
 

try:
    print('Connecting to SMTP server {}:{}...'.format(SMTP_SERVER, SMTP_PORT))
    s = smtp_connect()
except smtplib.SMTPServerDisconnected:
    print('...timed out. Please check your SMTP settings in .env')
    sys.exit(1)
smtp_login(s)
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

# check Odoo settings
ODOO_PORT = os.environ.get('NGINX_ODOO_ODOO_PORT', '8069')
ODOO_HOST = os.environ.get('NGINX_ODOO_ODOO_HOST', 'localhost')
ODOO_DATABASE = os.environ.get('NGINX_ODOO_ODOO_DATABASE')
if not ODOO_DATABASE:
    sys.exit('Odoo settings not set in .env')

# try to connect to odoo
try:
    odoo = odoorpc.ODOO(ODOO_HOST, port=ODOO_PORT)
except Exception:
    sys.exit('Odoo not running at {}:{}'.format(
        ODOO_HOST, ODOO_PORT))
databases = odoo.db.list()
if ODOO_DATABASE not in databases:
    sys.exit('Database {} not present at {}:{}'.format(
        ODOO_DATABASE, ODOO_HOST, ODOO_PORT))

auth_params = {
    'host': ODOO_HOST,
    'port': ODOO_PORT,
    'database': ODOO_DATABASE,
}
OdooAuthHandler.set_params(auth_params)

theme_params = {
  'backgroundcolor': BACKGROUNDCOLOR,
  'buttoncolor': BUTTONCOLOR,
  'buttonshadowcolor': BUTTONSHADOWCOLOR,
  'buttonhovercolor': BUTTONHOVERCOLOR,
  'branding': BRANDING,
}

app = application = bottle.Bottle()


# Static Routes (CSS, images)
@app.route("/static/<filepath:re:.*\.(css|jpg|png)>", method='GET')
def css(filepath):
    return static_file(filepath, root="static")


# Session login
@app.route('/web/session/authenticate', method='POST')
def authenticate():
    params = request.json.get('params')
    database = params.get('db')
    username = params.get('login')
    password = params.get('password')
    hotp_code = params.get('hotp_code')
    hotp_counter = params.get('hotp_counter')
    hotp_csrf = params.get('hotp_csrf')
    if not username and not password:
        return bottle.HTTPResponse(status=400)
    if not (hotp_code and hotp_counter and hotp_csrf):
        handler = OdooAuthHandler()
        data, session_id = handler.check_login(username, password)
        if not session_id:
            return bottle.HTTPResponse(status=401)
        hotp = pyotp.HOTP(HOTP_SECRET)
        hotp_counter, hotp_csrf = db.next_hotp_id(session_id)
        hotp_code = hotp.at(hotp_counter)
        # TODO: keep a logfile about sent mails
        if not send_mail(username, hotp_code):
            # for obfuscation, this needs to be the same as above
            return bottle.HTTPResponse(status=401)
        # TODO: finetune
        return {
            'hotp_counter': hotp_counter,
            'hotp_csrf': hotp_csrf,
        }
    else:
        hotp = pyotp.HOTP(HOTP_SECRET)
        if not hotp.verify(hotp_code, int(hotp_counter)):
            return bottle.HTTPResponse(status=401)
        session_id = db.verify_code_and_expiry(
            hotp_counter, hotp_csrf)
        # login again and return new session id
        data, session_id = handler.check_login(username, password)
        if not session_id:
            # for obfuscation, this needs to be the same as above
            return bottle.HTTPResponse(status=401)
        # save new session id, not old one
        db.save_session(session_id)
        return data


# Session logout
@app.route('/logout', method='GET')
def logout_session():
    session = request.get_cookie('session_id')
    db.remove_session(session)
    return redirect('/')


# Session verification
@app.route('/auth', method='GET')
def verify_session():
    session = request.get_cookie('session_id')
    if db.verify_session(session):
        return bottle.HTTPResponse(status=200)
    return bottle.HTTPResponse(status=401)


# Login page
@app.route('/', method='GET')
def login_page():
    # TODO: extra protection eg. by IP or browser signature
    return template('login', theme_params)


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
    if BRANDING:
        msgtext = "{} security code: {}".format(BRANDING, code)
    else:
        msgtext = "Security code: {}".format(code)
    msg = MIMEText(msgtext)
    msg['Subject'] = msgtext
    msg['From'] = SMTP_FROM
    msg['To'] = _to
    try:
        s = smtp_connect()
        smtp_login(s)
    except smtplib.SMTPServerDisconnected:
        pass  # log something or warn
    s.sendmail(SMTP_FROM, _to_list, msg.as_string())
    s.quit()
    s.close()
    return True


# Handle login
@app.route('/', method='POST')
def do_verify():

    # handle username/password
    # TODO: CSRF protection
    username = request.forms.get('username')
    password = request.forms.get('password')
    if username and password:
        handler = OdooAuthHandler()
        data, session_id = handler.check_login(username, password)
        if session_id:
            hotp = pyotp.HOTP(HOTP_SECRET)
            counter, code = db.next_hotp_id(session_id)
            key = hotp.at(counter)
            # TODO: keep a logfile about sent mails
            if not send_mail(username, key):
                # TODO: show failed message
                # https://github.com/polonel/SnackBar
                return redirect('/')
            return template(
                'hotp', dict(theme_params.items(), counter=counter, code=code))
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

class StripPathMiddleware(object):
    '''
    Get that slash out of the request
    '''
    def __init__(self, a):
        self.a = a
    def __call__(self, e, h):
        e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
        return self.a(e, h)


# this part will run when file is started directly
# but not when started with uWSGI
if __name__ == '__main__':

    # this is just for debug purposes; production runs on UWSGI
    bottle.run(
        app=StripPathMiddleware(app),
        host=LISTEN_HOST,
        port=LISTEN_PORT)

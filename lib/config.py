import os
import sys
import logging
from pathlib import Path

from lib.db import DB
from lib.odooauth import OdooAuthHandler

assert sys.version_info.major == 3, "Requires Python 3."


import os
import sys
from dotenv import load_dotenv


SCRIPT_PATH = os.path.abspath(os.path.dirname(__file__))
os.environ['BOUNCER_WORK_DIR'] = os.path.realpath(os.path.join(SCRIPT_PATH, ".."))
load_dotenv(os.path.join(os.environ["BOUNCER_WORK_DIR"], ".env"), override=True)

BOUNCER_ADMIN_USER_ODOO = os.environ["BOUNCER_ADMIN_USER_ODOO"]
BOUNCER_BACKGROUND_COLOR_ODOO = os.environ["BOUNCER_BACKGROUND_COLOR_ODOO"]
BOUNCER_BRANDING_ODOO = os.environ["BOUNCER_BRANDING_ODOO"]
BOUNCER_BUTTON_COLOR_ODOO = os.environ["BOUNCER_BUTTON_COLOR_ODOO"]
BOUNCER_BUTTON_HOVER_COLOR_ODOO = os.environ["BOUNCER_BUTTON_HOVER_COLOR_ODOO"]
BOUNCER_BUTTON_SHADOW_COLOR_ODOO = os.environ["BOUNCER_BUTTON_SHADOW_COLOR_ODOO"]
BOUNCER_DISABLE_EMAIL_ODOO = os.environ["BOUNCER_DISABLE_EMAIL_ODOO"]
BOUNCER_EXPIRY_INTERVAL_ODOO = os.environ["BOUNCER_EXPIRY_INTERVAL_ODOO"]
BOUNCER_HOTP_SECRET_ODOO = os.environ["BOUNCER_HOTP_SECRET_ODOO"]
BOUNCER_LISTEN_HOST_ODOO = os.environ["BOUNCER_LISTEN_HOST_ODOO"]
BOUNCER_LISTEN_PORT_ODOO = os.environ["BOUNCER_LISTEN_PORT_ODOO"]
BOUNCER_ODOO_DATABASE_ODOO = os.environ["BOUNCER_ODOO_DATABASE_ODOO"]
BOUNCER_ODOO_URL_ODOO = os.environ["BOUNCER_ODOO_URL_ODOO"]
BOUNCER_SMTP_FROM_ODOO = os.environ["BOUNCER_SMTP_FROM_ODOO"]
BOUNCER_SMTP_PASS_ODOO = os.environ["BOUNCER_SMTP_PASS_ODOO"]
BOUNCER_SMTP_PORT_ODOO = os.environ["BOUNCER_SMTP_PORT_ODOO"]
BOUNCER_SMTP_SERVER_ODOO = os.environ["BOUNCER_SMTP_SERVER_ODOO"]
BOUNCER_SMTP_SSL_ODOO = os.environ["BOUNCER_SMTP_SSL_ODOO"]
BOUNCER_SMTP_TO_ODOO = os.environ["BOUNCER_SMTP_TO_ODOO"]
BOUNCER_SMTP_USER_ODOO = os.environ["BOUNCER_SMTP_USER_ODOO"]


logging.basicConfig(level=logging.INFO)

_logger = logging.getLogger(__name__)

# load and check HOTP secret
HOTP_SECRET = os.environ.get("BOUNCER_HOTP_SECRET_ODOO")
hotp_secret_length = len(HOTP_SECRET) if HOTP_SECRET else 0
if hotp_secret_length != 32:
    sys.exit(
        "HOTP secret in .env must be 32 characters, has {}".format(hotp_secret_length)
    )

# load and check listen settings
# (when running as a developer, from command line instead of with uwsgi)
LISTEN_PORT = os.environ.get("BOUNCER_LISTEN_PORT_ODOO", 8888)
LISTEN_HOST = os.environ.get("BOUNCER_LISTEN_HOST_ODOO", "localhost")

# other settings
EXPIRY_INTERVAL = os.environ.get("BOUNCER_EXPIRY_INTERVAL_ODOO", "+16 hours")


# Email
# load and check email settings
SMTP_SERVER = os.environ.get("BOUNCER_SMTP_SERVER_ODOO")
SMTP_SSL = os.environ.get("BOUNCER_SMTP_SSL_ODOO")
SMTP_PORT = os.environ.get("BOUNCER_SMTP_PORT_ODOO", 465 if SMTP_SSL else 25)
SMTP_FROM = os.environ.get("BOUNCER_SMTP_FROM_ODOO")
ADMIN_USER = os.environ.get("BOUNCER_ADMIN_USER_ODOO", "admin")
SMTP_TO = os.environ.get("BOUNCER_SMTP_TO_ODOO")
SMTP_USER = os.environ.get("BOUNCER_SMTP_USER_ODOO")
SMTP_PASS = os.environ.get("BOUNCER_SMTP_PASS_ODOO")

# Database
# open database
user_home_dir = os.path.expanduser("~")
user_config_dir = os.path.expanduser("~") + "/.config/nginx-odoo"
Path(user_config_dir).mkdir(parents=True, exist_ok=True)
db_path = user_config_dir + "/database.db"
db = DB(db_path)
os.chmod(db_path, 0o600)
db_perm = os.stat(db_path).st_mode & 0o777
if db_perm != 0o600:
    sys.exit(
        "File permissions of {} must be 600 but are: {:o}".format(db_path, db_perm)
    )
db.cleanup()


# Odoo
# check Odoo settings
ODOO_URL = os.environ.get("BOUNCER_ODOO_URL_ODOO", "http://localhost:8069")
if ODOO_URL.endswith("/"):
    ODOO_URL = ODOO_URL[:-1]
ODOO_DATABASE = os.environ.get("BOUNCER_ODOO_DATABASE_ODOO")
if not ODOO_DATABASE:
    sys.exit("Odoo settings not set in .env")

# try to connect to odoo
try:
    odoo = OdooAuthHandler()
    odoo.test(ODOO_URL)
except Exception:
    _logger.warning("Odoo not running at {}".format(ODOO_URL))

auth_params = {
    "url": ODOO_URL + "/web/session/authenticate",
    "url_punchout_login": ODOO_URL + "/punchouttokenlogin",
    "url_punchout_signup": ODOO_URL + "/punchout/signup",
    "database": ODOO_DATABASE,
}
OdooAuthHandler.set_params(auth_params)


# Branding
# load and check branding settings
BRANDING = os.environ.get("BOUNCER_BRANDING_ODOO", "")
BACKGROUNDCOLOR = os.environ.get("BOUNCER_BACKGROUND_COLOR_ODOO", "")
BUTTONCOLOR = os.environ.get("BOUNCER_BUTTON_COLOR_ODOO", "")
BUTTONHOVERCOLOR = os.environ.get("BOUNCER_BUTTON_HOVER_COLOR_ODOO", "")
BUTTONSHADOWCOLOR = os.environ.get("BOUNCER_BUTTON_SHADOW_COLOR_ODOO", "")

theme_params = {
    "backgroundcolor": BACKGROUNDCOLOR,
    "buttoncolor": BUTTONCOLOR,
    "buttonshadowcolor": BUTTONSHADOWCOLOR,
    "buttonhovercolor": BUTTONHOVERCOLOR,
    "branding": BRANDING,
}

# Debug
disable_email = os.environ.get("BOUNCER_DISABLE_EMAIL_ODOO", "false").lower() == "true"

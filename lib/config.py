import os
import sys
import logging
from pathlib import Path

from lib.db import DB
from lib.odooauth import OdooAuthHandler

assert sys.version_info.major == 3, "Requires Python 3."

logging.basicConfig(level=logging.INFO)

_logger = logging.getLogger(__name__)

# load and check HOTP secret
HOTP_SECRET = os.environ.get("NGINX_ODOO_HOTP_SECRET")
hotp_secret_length = len(HOTP_SECRET) if HOTP_SECRET else 0
if hotp_secret_length != 32:
    sys.exit(
        "HOTP secret in .env must be 32 characters, has {}".format(hotp_secret_length)
    )

# load and check listen settings
# (when running as a developer, from command line instead of with uwsgi)
LISTEN_PORT = os.environ.get("NGINX_ODOO_LISTEN_PORT", 8888)
LISTEN_HOST = os.environ.get("NGINX_ODOO_LISTEN_HOST", "localhost")

# other settings
EXPIRY_INTERVAL = os.environ.get("NGINX_ODOO_EXPIRY_INTERVAL", "+16 hours")


# Email
# load and check email settings
SMTP_SERVER = os.environ.get("NGINX_ODOO_SMTP_SERVER")
SMTP_SSL = os.environ.get("NGINX_ODOO_SMTP_SSL")
SMTP_PORT = os.environ.get("NGINX_ODOO_SMTP_PORT", 465 if SMTP_SSL else 25)
SMTP_FROM = os.environ.get("NGINX_ODOO_SMTP_FROM")
SMTP_TO = os.environ.get("NGINX_ODOO_SMTP_TO")
SMTP_USER = os.environ.get("NGINX_ODOO_SMTP_USER")
SMTP_PASS = os.environ.get("NGINX_ODOO_SMTP_PASS")


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
ODOO_URL = os.environ.get("NGINX_ODOO_ODOO_URL", "http://localhost:8069")
if ODOO_URL.endswith("/"):
    ODOO_URL = ODOO_URL[:-1]
ODOO_DATABASE = os.environ.get("NGINX_ODOO_ODOO_DATABASE")
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
BRANDING = os.environ.get("NGINX_ODOO_BRANDING", "")
BACKGROUNDCOLOR = os.environ.get("NGINX_ODOO_BACKGROUND_COLOR", "")
BUTTONCOLOR = os.environ.get("NGINX_ODOO_BUTTON_COLOR", "")
BUTTONHOVERCOLOR = os.environ.get("NGINX_ODOO_BUTTON_HOVER_COLOR", "")
BUTTONSHADOWCOLOR = os.environ.get("NGINX_ODOO_BUTTON_SHADOW_COLOR", "")
DEFAULT_LOGIN = os.environ.get("NGINX_ODOO_DEFAULT_LOGIN", r"./templates/login-2.html")
DEFAULT_HOTP = os.environ.get("NGINX_ODOO_DEFAULT_HOTP", r"./templates/hotp-2.html")

theme_params = {
    "backgroundcolor": BACKGROUNDCOLOR,
    "buttoncolor": BUTTONCOLOR,
    "buttonshadowcolor": BUTTONSHADOWCOLOR,
    "buttonhovercolor": BUTTONHOVERCOLOR,
    "branding": BRANDING,
}

# Debug
disable_email = os.environ.get("NGINX_ODOO_DISABLE_EMAIL", "false").lower() == "true"

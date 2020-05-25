#!/bin/env python

import pyotp

print(
    "Copypaste this line into .env:\n"
    "NGINX_ODOO_HOTP_SECRET={}".format(
        pyotp.random_base32()),
)

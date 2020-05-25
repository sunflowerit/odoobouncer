#!/bin/env python

import pyotp

print(
    "Copypaste this line into .envrc:\n"
    "export NGINX_ODOO_HOTP_SECRET='{}'".format(
        pyotp.random_base32()),
)

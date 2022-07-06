#!/bin/env python

import pyotp

print(
    "Copypaste this line into .env:\n"
    "BOUNCER_HOTP_SECRET_ODOO={}".format(pyotp.random_base32()),
)

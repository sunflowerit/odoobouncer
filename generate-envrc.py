#!/bin/env python

import pyotp

print(
    "export FFHOTP_SECRET='{}'".format(
        pyotp.random_base32()),
)

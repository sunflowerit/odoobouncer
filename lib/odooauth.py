#!/bin/env python
# Copyright 2020 Sunflower IT

import logging
import odoorpc
import urllib


class OdooAuthHandler():

    params = {
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
            logging.info(
                'Authenticating host %s port %s database %s user %s',
                host, port, database, username)
            data = odoo.json('/web/session/authenticate', {
                'db': database, 'login': username, 'password': password
            })
            cookie_processor = [
                handler for handler in odoo._connector._opener.handlers
                if isinstance(handler, urllib.request.HTTPCookieProcessor)
            ]
            if not cookie_processor:
                logging.info('Authentication failed: cookiejar not found')
                return False, False
            cookiejar = cookie_processor[0].cookiejar
            cookies = [cookie for cookie in list(cookiejar) if cookie.name == 'session_id']
            if not cookies or not cookies[0].value:
                logging.info('Authentication failed: session cookie not found')
            result = data.get('result')
            if not result.get('uid'):
                logging.info('Authentication failed: no uid in response')
                return False, False
            # TODO: check user object for the 'portal flag'
            session_id = cookies[0].value
            return data, session_id
        except (odoorpc.error.RPCError, urllib.error.URLError) as e:
            logging.error('Odoo exception: %s', str(e))
            return False, False

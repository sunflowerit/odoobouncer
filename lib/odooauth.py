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
            result = data.get('result')
            session_id = result.get('session_id')
            if not result.get('uid') or not session_id:
                logging.info('Authentication failed')
                return False, False
            # TODO: check user object for the 'portal flag'
            return data, session_id
        except (odoorpc.error.RPCError, urllib.error.URLError) as e:
            logging.error('Odoo exception: %s', str(e))
            return False, False

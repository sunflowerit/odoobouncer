#!/bin/env python
# Copyright 2020 Sunflower IT

import logging
import random
import httpx
import asyncio
from pprint import pformat


class OdooAuthHandler():

    params = {
        'url': None,
        'database': None,
    }

    @classmethod
    def set_params(cls, params):
        cls.params = params

    async def request_odoo(self,url,params):
        async with httpx.AsyncClient() as client:
            json_payload = {'jsonrpc':'2.0',
                'method':'call',
                'params':params,
                'id':random.randint(0,1000000000)}
            return await client.post(url,json=json_payload)

    async def check_login(self, username, password):
        database = self.params.get('database')
        url=self.params.get('url')
        params={
            'db':database,
            'login':username,
            'password':password
        }
        resp=await self.request_odoo(url,params)
        if not 'session_id' in resp.cookies:
            logging.info('Authentication failed: session cookie not found')
            return False, False
        cookie=resp.cookies['session_id']
        result=resp.json()
        if not 'result' in result:
            logging.info('Authentication failed')
            if 'error' in result:
                logging.info(pformat(result['error']))
            return False, False
        elif not result['result'].get('uid'):
            logging.info('Authentication failed: no uid in response')
            return False, False
        return result,cookie

    def test(self,url):
        loop=asyncio.get_event_loop()
        loop.run_until_complete(self.request_odoo(url+'/jsonrpc',{
            'service':'common',
            'method':'version',
            'args':()
        }))

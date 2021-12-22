#!/bin/env python
# Copyright 2020 Sunflower IT

import asyncio
import httpx
import logging
import random
import traceback

from pprint import pformat


class OdooAuthHandler:

    params = {
        "url": None,
        "url_punchout_login": None,
        "url_punchout_signup": None,
        "database": None,
    }

    @classmethod
    def set_params(cls, params):
        cls.params = params

    async def request_odoo(self, url, params):
        async with httpx.AsyncClient(timeout=20) as client:
            json_payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": params,
                "id": random.randint(0, 1000000000),
            }
            return await client.post(url, json=json_payload)

    async def check_login(self, username, password):
        database = self.params.get("database")
        url = self.params.get("url")
        params = {"db": database, "login": username, "password": password}
        try:
            resp = await self.request_odoo(url, params)
        except (httpx.ConnectError, httpx.TimeoutException):
            logging.error(traceback.format_exc())
            return False, False
        if not "session_id" in resp.cookies:
            logging.info("Authentication failed: session cookie not found")
            return False, False
        cookie = resp.cookies["session_id"]
        result = resp.json()
        if not "result" in result:
            logging.info("Authentication failed")
            if "error" in result:
                logging.info(pformat(result["error"]))
            return False, False
        elif not result["result"].get("uid"):
            logging.info("Authentication failed: no uid in response")
            return False, False
        return result, cookie

    async def punchout_login(self, token):
        url = self.params.get("url_punchout_login")
        params = {"token": token}
        async with httpx.AsyncClient(timeout=20) as client:
            try:
                resp = await client.get(url, params=params)
            except (httpx.ConnectError, httpx.TimeoutException):
                logging.error(traceback.format_exc())
                return False, False
            if resp.status_code != 200:
                logging.info("Authentication failed for punchout login")
                return False, False
        if not "session_id" in resp.cookies:
            logging.info("Session cookie not found for punchout login")
            return False, False
        cookie = resp.cookies["session_id"]
        return resp, cookie

    async def punchout_signup(self, token, session_id):
        url = self.params.get("url_punchout_signup")
        params = {"signup_token": token}
        cookies = {}
        if session_id:
            cookies["session_id"] = session_id
        async with httpx.AsyncClient(timeout=20) as client:
            try:
                resp = await client.get(url, params=params, cookies=cookies)
                if resp.status_code != 200:
                    logging.info("Authentication failed for punchout signup")
                    return False, False
            except (httpx.ConnectError, httpx.TimeoutException):
                logging.error(traceback.format_exc())
                return False, False
        if not "session_id" in resp.cookies:
            logging.info("Session cookie not found for punchout signup")
            return False, False
        session_id = resp.cookies["session_id"]
        return resp, session_id

    async def punchout_signup_post(self, token, post_params, session_id):
        url = self.params.get("url_punchout_signup")
        params = {"signup_token": token}
        cookies = {}
        if session_id:
            cookies["session_id"] = session_id
        async with httpx.AsyncClient(timeout=20) as client:
            try:
                resp = await client.post(url, params=params, data=post_params, cookies=cookies)
            except (httpx.ConnectError, httpx.TimeoutException):
                logging.error(traceback.format_exc())
                return False, False
            if resp.status_code != 200:
                logging.info("Authentication failed for punchout signup post")
                return False, False
        if not "session_id" in resp.cookies:
            logging.info("Session cookie not found for punchout signup post")
            return False, False
        cookie = resp.cookies["session_id"]
        return resp, cookie

    def test(self, url):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            self.request_odoo(
                url + "/jsonrpc", {"service": "common", "method": "version", "args": ()}
            )
        )

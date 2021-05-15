#!/bin/env python
# Copyright 2020 Sunflower IT

# TODO: for extra safety, dont let session_id be Odoo session id,
# but make a new JWT token that includes the Odoo session id,
# and translate in NGINX.
# TODO: prevent people logging out, but setting session_id again
# with cookie manager, then coming to Odoo login screen and
# guessing admin password.

from tornado.web import Application,RequestHandler,StaticFileHandler
import tornado.ioloop
import tornado.escape
import asyncio

import logging
import odoorpc
import pyotp

import lib.config as config
db=config.db
OdooAuthHandler=config.OdooAuthHandler

from lib.email import email

# Login page and login check
class LoginHandler(RequestHandler):
  def get(self):
    # TODO: extra protection eg. by IP or browser signature

    # Redirect to other service
    # needed when using the bouncer to authenticate a user with the bouncer
    redirect_url=self.get_argument('redirect',None)
    if redirect_url!=None:
      session_id=self.get_cookie('session_id')
      if db.verify_session(session_id):
        if not redirect_url.endswith('/'):
          redirect_url+='/'
        return self.redirect(f'{redirect_url}auth/{session_id}')
    self.render(r'./templates/login.html',**config.theme_params)
  async def post(self):
    # handle username/password
    # TODO: CSRF protection
    username=self.get_body_argument('username',default=None)
    password=self.get_body_argument('password',default=None)
    if username and password:
      logging.info('Verifying username %s and password...', username)
      handler = OdooAuthHandler()
      data, session_id = handler.check_login(username, password)
      if session_id:
        hotp = pyotp.HOTP(config.HOTP_SECRET)
        counter, code = db.next_hotp_id(session_id)
        key = hotp.at(counter)
        if config.disable_email:
          # Display hotp in the log in stead of sending an email
          logging.info(f'HOTP code: {key}')
        else:
          if not await email.send(username, key):
            message = 'Mail with security code not sent.'
            logging.error(message)
            return self.render(r'./templates/login.html',**config.theme_params,error=message)
        return self.render(r'./templates/hotp.html',**config.theme_params,counter=counter,code=code)
      else:
        # TODO: brute force protection
        #       (block for X minutes after X attempts)
        message = 'Invalid username or password.'
        logging.info(message)
        return self.render(r'./templates/login.html',**config.theme_params,error=message)

    # check HOTP
    counter=self.get_body_argument('counter',default=None)
    code=self.get_body_argument('code',default=None)
    hotp_code=self.get_body_argument('hotp_code',default=None)
    if code and counter and hotp_code:
      hotp = pyotp.HOTP(config.HOTP_SECRET)
      if not hotp.verify(hotp_code, int(counter)):
        message = 'Invalid security code.'
        return self.render(r'./templates/login.html',**config.theme_params,error=message)
      session_id = db.verify_code_and_expiry(counter, code)
      if not session_id:
        message = 'Invalid security code (2).'
        return self.render(r'./templates/login.html',**config.theme_params,error=message)
      db.save_session(session_id, config.EXPIRY_INTERVAL)
      logging.info('Setting session cookie: %s', session_id)
      self.set_cookie('session_id',session_id,path='/')
      # Redirect to other service
      # needed when using the bouncer to authenticate a user with the bouncer
      redirect_url=self.get_argument('redirect','/')
      if redirect_url!='/':
        if not redirect_url.endswith('/'):
          redirect_url+='/'
        redirect_url=f'{redirect_url}auth/{session_id}'
      return self.redirect(redirect_url)
    return self.redirect('/')

# Session verificaiton
class VerifySessionHandler(RequestHandler):
  def get(self):
    session=self.get_cookie('session_id')
    if db.verify_session(session):
      self.set_status(200)
    else:
      logging.error(f'Failed to verify session: {session}')
      self.set_status(401)
    self.finish()

# Session logout
class LogoutHandler(RequestHandler):
  def get(self):
    session=self.get_cookie('session_id')
    db.remove_session(session)
    return self.redirect('/')

# Session login
class AuthenticateHandler(RequestHandler):
  async def post(self):
    params=tornado.escape.json_decode(self.request.body)['params']
    database=params['db'] if 'db' in params else None
    username=params['login'] if 'login' in params else None
    password=params['password'] if 'password' in params else None
    hotp_code=params['hotp_code'] if 'hotp_code' in params else None
    hotp_counter=params['hotp_counter'] if 'hotp_counter' in params else None
    hotp_csrf=params['hotp_csrf'] if 'hotp_csrf' in params else None
    if not username and not password:
      return self.set_status(400)
    if not (hotp_code and hotp_counter and hotp_csrf):
      handler = OdooAuthHandler()
      data, session_id = handler.check_login(username, password)
      if not session_id:
        return self.set_status(401)
      hotp = pyotp.HOTP(config.HOTP_SECRET)
      hotp_counter, hotp_csrf = db.next_hotp_id(session_id)
      hotp_code = hotp.at(hotp_counter)
      if config.disable_email:
        # Display hotp in the log in stead of sending an email
        logging.info(f'HOTP code: {hotp_code}')
      else:
        if not await email.send(username, hotp_code):
          # for obfuscation, this needs to be the same as above
          return self.set_status(401)
      return self.write({
        'result': {
          'hotp_counter': hotp_counter,
          'hotp_csrf': hotp_csrf,
        }
      })
    else:
      hotp = pyotp.HOTP(config.HOTP_SECRET)
      # TODO: memory leaks?
      handler = OdooAuthHandler()
      if not hotp.verify(hotp_code, int(hotp_counter)):
        return self.set_status(401)
      session_id = db.verify_code_and_expiry(
        hotp_counter, hotp_csrf)
      # login again and return new session id
      data, session_id = handler.check_login(username, password)
      if not session_id:
        # for obfuscation, this needs to be the same as above
        return self.set_status(401)
      # save new session id, not old one
      db.save_session(session_id, config.EXPIRY_INTERVAL)
      return self.write(data)

app=Application([
  (r'/',LoginHandler),
  (r'/auth/?',VerifySessionHandler),
  (r'/logout/?',LogoutHandler),
  (r'/static/(.*\.(css|jpg|png))/?',StaticFileHandler,{'path':r'./static'}),
  (r'/web/session/authenticate/?',AuthenticateHandler)
], debug=True)

if __name__=='__main__':
  # Check connection with email service
  loop=asyncio.get_event_loop()
  loop.run_until_complete(email.test())

  app.listen(config.LISTEN_PORT)
  print(f'Listening at port {config.LISTEN_PORT}')
  tornado.ioloop.IOLoop.current().start()

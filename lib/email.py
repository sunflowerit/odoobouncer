import aiosmtplib
import lib.config as config
import logging
import re

from email.mime.text import MIMEText

class email:
	connected=False
	email_regex = re.compile(
		r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$")
	async def connect():
		if config.SMTP_SSL:
			s = aiosmtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=5, use_tls=True)
		else:
			s = aiosmtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=5, use_tls=False)
		await s.connect()
		return s

	async def login(s):
		if config.SMTP_USER:
			await s.login(config.SMTP_USER, config.SMTP_PASS)
		return

	async def full_connect():
		try:
			logging.info('Connecting to SMTP server {}:{}...'.format(config.SMTP_SERVER, config.SMTP_PORT))
			s = await email.connect()
			await email.login(s)
			s.close()
			email.connected = True
		except aiosmtplib.SMTPServerDisconnected:
			logging.info('...timed out. Please check your SMTP settings in .env')
		except Exception as e:
			logging.info(str(e))

	async def test():
		if not config.SMTP_SERVER or not config.SMTP_FROM:
			sys.exit('SMTP settings not set in .env')

		try:
			logging.info('Connecting to SMTP server {}:{}...'.format(config.SMTP_SERVER, config.SMTP_PORT))
			s = await email.connect()
		except aiosmtplib.SMTPServerDisconnected:
			logging.info('...timed out. Please check your SMTP settings in .env')
			sys.exit(1)
		await email.login(s)
		s.close()

	async def send(username, code):
		if not email.connected:
			await email.full_connect()
		if username == 'admin' and config.SMTP_TO:
			_to = config.SMTP_TO
		else:
			_to = username
		if not _to:
			return False
		_to_list = _to.split(',')
		if not all(email.email_regex.match(t) for t in _to_list):
			return False
		if config.BRANDING:
			msgtext = "{} security code: {}".format(config.BRANDING, code)
		else:
			msgtext = "Security code: {}".format(code)
		msg = MIMEText(msgtext)
		msg['Subject'] = msgtext
		msg['From'] = config.SMTP_FROM
		msg['To'] = _to
		s = None
		retries = 3
		success = False
		logging.info('Trying to send mail..')
		while (not success) and retries > 0:
			try:
				s = await email.connect()
				await email.login(s)
				await s.sendmail(config.SMTP_FROM, _to_list, msg.as_string())
				await s.quit()
				s.close()
				success = True
				break
			except aiosmtplib.SMTPServerDisconnected:
				retries -= 1
		if not success:
			logging.error('SMTP failed after three retries')
			return False
		logging.info('Mail with security code sent to %s', _to)
		return True

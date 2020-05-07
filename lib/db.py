import dateutil.parser
import random
import sqlite3
import string

from datetime import datetime


class DB(object):    
    """DB initializes and manipulates SQLite3 databases."""

    session_cache = {}

    def __init__(self, database='database.db', statements=[]):
        """Initialize a new or connect to an existing database."""

        self.database = database
        self.create_tables()
        self.load_sessions()

    def remove_session(self, session):
        self.session_cache.pop(session)
        con = self.connect()
        cur = con.cursor()
        cur.execute('''
            delete from odoo_sessions where session_id = ?
        ''', (session,))
        con.commit()
        con.close()

    def verify_session(self, session):
        session_data = self.session_cache.get(session)
        if not session_data:
            return False
        expiry = session_data.get('expiry')
        if expiry < datetime.utcnow():
            return False
        return True

    def load_sessions(self):
        con = self.connect()
        cur = con.cursor()
        cur.execute('''
            select session_id, expiry from odoo_sessions
        ''')
        for row in cur:
            session = row[0]
            expiry = row[1]
            self.session_to_cache(session, expiry)
        con.close()

    def session_to_cache(self, session, expiry_string):
        # decode string to python datetime
        expiry = dateutil.parser.parse(expiry_string)
        self.session_cache[session] = {'expiry': expiry}

    def save_session(self, session):
        con = self.connect()
        cur = con.cursor()
        cur.execute('''
            insert into odoo_sessions (session_id, expiry)
            select ?, datetime(datetime(), '+15 minutes')
        ''', (session,))
        _id = cur.lastrowid
        cur.execute('''
            select expiry from odoo_sessions where id = ?
        ''', (_id,))
        row = cur.fetchone()
        expiry = row[0]
        self.session_to_cache(session, expiry)
        con.commit()
        con.close()
        return _id, expiry

    def next_hotp_id(self, session_id):
        con = self.connect()
        cur = con.cursor()
        # A random code to be provided by the form
        code = ''.join(
            random.SystemRandom().choice(
                string.ascii_uppercase + string.digits
            ) for _ in range(16)
        )
        cur.execute('''
            insert into hotp_codes (expiry, code, session_id)
            select datetime(datetime(), '+15 minutes'), ?, ?
        ''', (code, session_id))
        _id = cur.lastrowid
        con.commit()
        con.close()
        return _id, code

    def verify_code_and_expiry(self, counter, code):
        # Verify random code provided by form
        con = self.connect()
        cur = con.cursor()
        cur.execute('''
            select id, session_id from hotp_codes
            where id = ? and code = ? and expiry > datetime('now')
        ''', (counter, code,))
        row = cur.fetchone()
        if row:
            cur.execute('''
                delete from hotp_codes where id = ?
            ''', (row[0],))
            con.commit()
            session_id = row[1]
        else:
            session_id = False
        con.close()
        return session_id

    def cleanup(self):
        # Cleanup: clear expired tokens, etc
        con = self.connect()
        cur = con.cursor()
        cur.execute('''
            delete from hotp_codes where expiry < datetime('now')
        ''')
        cur.execute('''
            delete from odoo_sessions where expiry < datetime('now')
        ''')
        con.commit()
        con.close()

    def create_tables(self):
        con = self.connect()
        cur = con.cursor()
        cur.execute('''
            create table if not exists hotp_codes (
                id integer primary key autoincrement,
                expiry datetime,
                code character(16),
                session_id character(20)
            )
        ''')
        cur.execute('''
            create table if not exists odoo_sessions (
                id integer primary key autoincrement,
                session_id character(20),
                expiry datetime
            )
        ''')
        cur.execute('''
            create unique index if not exists idx_session_id
            on odoo_sessions (session_id)
        ''')
        con.commit()
        con.close()

    def connect(self):
        """Connect to the SQLite3 database."""

        return sqlite3.connect(self.database)

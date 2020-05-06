import random
import sqlite3
import string


class DB(object):    
    """DB initializes and manipulates SQLite3 databases."""

    def __init__(self, database='database.db', statements=[]):
        """Initialize a new or connect to an existing database."""

        self.database = database
        self.create_tables()

    def next_hotp_id(self):
        con = self.connect()
        cur = con.cursor()
        # A random code to be provided by the form
        code = ''.join(
            random.SystemRandom().choice(
                string.ascii_uppercase + string.digits
            ) for _ in range(16)
        )
        cur.execute('''
            insert into hotp_codes (expiry, code)
            select datetime(datetime(), '+15 minutes'), ?
        ''', (code,))
        id = cur.lastrowid
        con.commit()
        con.close()
        return id, code

    def verify_code_and_expiry(self, counter, code):
        # Verify random code provided by form
        con = self.connect()
        cur = con.cursor()
        cur.execute('''
            select id from hotp_codes
            where id = ? and code = ? and expiry > datetime('now')
        ''', (counter, code,))
        row = cur.fetchone()
        if row:
            cur.execute('''
                delete from hotp_codes where id = ?
            ''', (row[0],))
            con.commit()
            res = True
        else:
            res = False
        con.close()
        return res

    def cleanup(self):
        # Cleanup: clear expired tokens, etc
        con = self.connect()
        cur = con.cursor()
        cur.execute('''
            delete from hotp_codes where expiry < datetime('now')
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
                code character(16)
            )
        ''')
        cur.execute('''
            create table if not exists odoo_sessions (
                session_id character(20) primary key,
                expiry datetime
            )
        ''')
        con.commit()
        con.close()

    def connect(self):
        """Connect to the SQLite3 database."""

        return sqlite3.connect(self.database)

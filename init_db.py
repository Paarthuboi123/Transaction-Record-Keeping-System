import sqlite3
import os
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'data.db')


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('owner','staff'))
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        counterparty TEXT NOT NULL,
        item TEXT NOT NULL,
        transaction_type TEXT NOT NULL,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        description TEXT,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        c.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?,?,?)',
            ('owner', generate_password_hash('ownerpass'), 'owner'),
        )
        c.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?,?,?)',
            ('staff', generate_password_hash('staffpass'), 'staff'),
        )
        print('Seeded users: owner/ownerpass, staff/staffpass')
    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    print('Initialized database at', DB_PATH)



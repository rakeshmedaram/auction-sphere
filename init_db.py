import sqlite3

conn = sqlite3.connect("database.db")

# USERS
conn.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT,
    role TEXT
)
''')

# AUCTIONS
conn.execute('''
CREATE TABLE auctions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    price INTEGER,
    image TEXT,
    end_time TEXT,
    owner TEXT,
    description TEXT
)
''')

# BIDS
conn.execute('''
CREATE TABLE bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_id INTEGER,
    user TEXT,
    amount INTEGER,
    time TEXT
)
''')

conn.commit()
conn.close()

print("Database created successfully!")
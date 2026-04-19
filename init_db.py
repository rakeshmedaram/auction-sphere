import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

# USERS
c.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT
)
""")

# AUCTIONS
c.execute("""
CREATE TABLE auctions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price INTEGER,
    description TEXT,
    end_time TEXT,
    created_by INTEGER
)
""")

# BIDS
c.execute("""
CREATE TABLE auctions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price INTEGER,
    description TEXT,
    end_time TEXT,
    created_by INTEGER,
    image TEXT
)
""")

conn.commit()
conn.close()

print("DB created")
import sqlite3

def get_db():
    return sqlite3.connect("database.db", check_same_thread=False)

def init_db():
    db = get_db()

    db.execute("""
    CREATE TABLE IF NOT EXISTS listas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        estado TEXT,
        resultado TEXT
    )
    """)

    db.commit()

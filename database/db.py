import sqlite3

DATABASE_PATH = 'research.db'

def get_db():
    """Connect to SQLite database and return connection with Row factory."""
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db
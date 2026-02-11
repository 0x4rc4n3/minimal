from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db
import sqlite3

def register_user(username, password):
    """Register a new user with username and password."""
    db = get_db()
    cursor = db.cursor()
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    password_hash = generate_password_hash(password)
    
    try:
        cursor.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (username, password_hash)
        )
        db.commit()
        db.close()
        return True, "User registered successfully"
    except sqlite3.IntegrityError:
        db.close()
        return False, "Username already exists"

def verify_credentials(username, password):
    """Verify username and password. Returns (user_id, error_code, error_message)."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    db.close()
    
    if not user:
        return None, "USER_NOT_FOUND", "Username not found"
    
    if check_password_hash(user['password_hash'], password):
        return user['id'], None, None
    else:
        return None, "INVALID_PASSWORD", "Incorrect password"
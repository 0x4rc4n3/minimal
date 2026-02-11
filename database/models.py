from database.db import get_db
from datetime import datetime
from werkzeug.security import generate_password_hash
import uuid

def init_db():
    """Initialize database tables with enhanced schema."""
    db = get_db()
    cursor = db.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            wallet_address TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Research sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS research_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            consent_given BOOLEAN DEFAULT 0,
            first_method TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # Auth attempts table (enhanced)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_id INTEGER,
            method TEXT,
            attempt_number INTEGER,
            duration_ms REAL,
            success BOOLEAN,
            error_code TEXT,
            error_message TEXT,
            user_agent TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES research_sessions(session_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Feedback table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            method TEXT,
            ease_of_use INTEGER,
            speed_rating INTEGER,
            security_feeling INTEGER,
            would_use_again BOOLEAN,
            comments TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES research_sessions(session_id)
        )
    ''')
    
    # Method education views (track when users see pros/cons)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS education_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            method TEXT,
            duration_seconds REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES research_sessions(session_id)
        )
    ''')
    
    db.commit()
    db.close()

def create_research_session():
    """Create a new research session and return session_id."""
    db = get_db()
    cursor = db.cursor()
    
    session_id = str(uuid.uuid4())
    cursor.execute(
        'INSERT INTO research_sessions (session_id) VALUES (?)',
        (session_id,)
    )
    db.commit()
    db.close()
    
    return session_id

def update_session_consent(session_id, consent_given):
    """Update consent status for session."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE research_sessions SET consent_given = ? WHERE session_id = ?',
        (consent_given, session_id)
    )
    db.commit()
    db.close()

def set_session_first_method(session_id, method):
    """Set the first method used in this session."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE research_sessions SET first_method = ? WHERE session_id = ?',
        (method, session_id)
    )
    db.commit()
    db.close()

def complete_session(session_id):
    """Mark session as completed."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'UPDATE research_sessions SET completed_at = ?, status = ? WHERE session_id = ?',
        (datetime.now(), 'completed', session_id)
    )
    db.commit()
    db.close()

def get_session_info(session_id):
    """Get session information."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM research_sessions WHERE session_id = ?', (session_id,))
    session = cursor.fetchone()
    db.close()
    return dict(session) if session else None

def create_test_user(username, password):
    """Create a test user with traditional credentials."""
    db = get_db()
    cursor = db.cursor()
    
    password_hash = generate_password_hash(password)
    
    try:
        cursor.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (username, password_hash)
        )
        db.commit()
        print(f"Test user '{username}' created successfully.")
    except Exception as e:
        print(f"User '{username}' already exists or error: {e}")
    finally:
        db.close()

def clear_all_data():
    """Clear all research data (admin function)."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('DELETE FROM education_views')
    cursor.execute('DELETE FROM feedback')
    cursor.execute('DELETE FROM auth_attempts')
    cursor.execute('DELETE FROM research_sessions')
    cursor.execute("DELETE FROM users WHERE username != 'test'")
    
    db.commit()
    db.close()
from database.db import get_db
from datetime import datetime
import time

def log_auth_attempt(session_id, user_id, method, attempt_number, start_time, success, 
                    error_code=None, error_message=None, user_agent=None):
    """Log an authentication attempt with comprehensive data."""
    db = get_db()
    cursor = db.cursor()
    
    duration_ms = (time.time() - start_time) * 1000
    
    cursor.execute('''
        INSERT INTO auth_attempts 
        (session_id, user_id, method, attempt_number, duration_ms, success, 
         error_code, error_message, user_agent, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, user_id, method, attempt_number, duration_ms, success, 
          error_code, error_message, user_agent, datetime.now()))
    
    db.commit()
    db.close()

def log_education_view(session_id, method, duration_seconds):
    """Log when user views educational content about a method."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        INSERT INTO education_views (session_id, method, duration_seconds, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (session_id, method, duration_seconds, datetime.now()))
    
    db.commit()
    db.close()

def save_feedback(session_id, method, ease_of_use, speed_rating, security_feeling, 
                 would_use_again, comments):
    """Save user feedback for a specific method."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        INSERT INTO feedback 
        (session_id, method, ease_of_use, speed_rating, security_feeling, 
         would_use_again, comments, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, method, ease_of_use, speed_rating, security_feeling,
          would_use_again, comments, datetime.now()))
    
    db.commit()
    db.close()

def get_session_attempts(session_id):
    """Get all auth attempts for a session."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT * FROM auth_attempts 
        WHERE session_id = ? 
        ORDER BY timestamp ASC
    ''', (session_id,))
    
    attempts = [dict(row) for row in cursor.fetchall()]
    db.close()
    return attempts

def get_all_sessions():
    """Get all research sessions with stats."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT 
            rs.*,
            COUNT(DISTINCT aa.id) as total_attempts,
            SUM(CASE WHEN aa.success = 1 THEN 1 ELSE 0 END) as successful_attempts,
            COUNT(DISTINCT f.id) as feedback_count
        FROM research_sessions rs
        LEFT JOIN auth_attempts aa ON rs.session_id = aa.session_id
        LEFT JOIN feedback f ON rs.session_id = f.session_id
        GROUP BY rs.id
        ORDER BY rs.started_at DESC
    ''')
    
    sessions = [dict(row) for row in cursor.fetchall()]
    db.close()
    return sessions

def get_analytics():
    """Get comprehensive analytics for admin dashboard."""
    db = get_db()
    cursor = db.cursor()
    
    # Overall stats
    cursor.execute('''
        SELECT 
            COUNT(DISTINCT session_id) as total_sessions,
            COUNT(*) as total_attempts,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_attempts,
            AVG(CASE WHEN success = 1 THEN duration_ms END) as avg_success_duration,
            AVG(CASE WHEN success = 0 THEN duration_ms END) as avg_failure_duration
        FROM auth_attempts
    ''')
    overall = dict(cursor.fetchone())
    
    # Method comparison
    cursor.execute('''
        SELECT 
            method,
            COUNT(*) as attempts,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
            AVG(duration_ms) as avg_duration,
            AVG(CASE WHEN success = 1 THEN duration_ms END) as avg_success_duration,
            COUNT(DISTINCT session_id) as unique_sessions
        FROM auth_attempts
        GROUP BY method
    ''')
    method_stats = [dict(row) for row in cursor.fetchall()]
    
    # Feedback analysis
    cursor.execute('''
        SELECT 
            method,
            AVG(ease_of_use) as avg_ease,
            AVG(speed_rating) as avg_speed,
            AVG(security_feeling) as avg_security,
            SUM(CASE WHEN would_use_again = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as would_use_percent,
            COUNT(*) as feedback_count
        FROM feedback
        GROUP BY method
    ''')
    feedback_stats = [dict(row) for row in cursor.fetchall()]
    
    # Error analysis
    cursor.execute('''
        SELECT 
            method,
            error_code,
            COUNT(*) as count
        FROM auth_attempts
        WHERE success = 0 AND error_code IS NOT NULL
        GROUP BY method, error_code
        ORDER BY count DESC
    ''')
    errors = [dict(row) for row in cursor.fetchall()]
    
    # Recent activity
    cursor.execute('''
        SELECT 
            aa.*,
            rs.started_at as session_start
        FROM auth_attempts aa
        JOIN research_sessions rs ON aa.session_id = rs.session_id
        ORDER BY aa.timestamp DESC
        LIMIT 50
    ''')
    recent = [dict(row) for row in cursor.fetchall()]
    
    db.close()
    
    return {
        'overall': overall,
        'by_method': method_stats,
        'feedback': feedback_stats,
        'errors': errors,
        'recent_activity': recent
    }
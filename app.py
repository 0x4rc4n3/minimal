from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from database.models import (init_db, create_test_user, create_research_session, 
                            update_session_consent, set_session_first_method,
                            complete_session, get_session_info, clear_all_data)
from auth.password import verify_credentials
from auth.crypto import verify_signature, get_user_by_wallet
from telemetry.logger import (
    log_auth_attempt,
    log_education_view,
    save_feedback,
    get_analytics,
    get_all_sessions
)
import uuid
import time
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Session configuration
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 7200  # 2 hours

# Admin password (change this!)
ADMIN_PASSWORD = "admin123"

def get_or_create_research_session():
    """Get existing research session or create new one."""
    if 'research_session_id' not in session:
        session['research_session_id'] = create_research_session()
        session['methods_completed'] = []
        session['current_step'] = 'intro'
    return session['research_session_id']

def determine_next_method():
    """Determine which auth method to show next based on what's been completed."""
    completed = session.get('methods_completed', [])
    
    if 'TRADITIONAL' not in completed:
        return 'TRADITIONAL'
    elif 'DID' not in completed:
        return 'DID'
    else:
        return None

@app.route('/')
def index():
    """Entry point - show introduction."""
    # Create new research session
    session.clear()
    session['research_session_id'] = create_research_session()
    session['methods_completed'] = []
    session['current_step'] = 'intro'
    return render_template('intro.html')

@app.route('/consent', methods=['POST'])
def consent():
    """Handle consent submission."""
    consent_given = request.form.get('consent') == 'yes'
    research_session_id = get_or_create_research_session()
    
    update_session_consent(research_session_id, consent_given)
    
    if consent_given:
        session['current_step'] = 'auth'
        return redirect(url_for('authenticate'))
    else:
        return render_template('no_consent.html')

@app.route('/authenticate')
def authenticate():
    """Show authentication page with assigned method."""
    if session.get('current_step') != 'auth':
        return redirect(url_for('index'))
    
    next_method = determine_next_method()
    
    if next_method is None:
        # Both methods completed, go to final feedback
        return redirect(url_for('final_feedback'))
    
    research_session_id = get_or_create_research_session()
    session_info = get_session_info(research_session_id)
    
    # Set first method if not set
    if not session_info['first_method']:
        set_session_first_method(research_session_id, next_method)
    
    session['current_method'] = next_method
    session['auth_attempt'] = session.get('auth_attempt', 0) + 1
    
    return render_template('authenticate.html', method=next_method)

@app.route('/api/nonce')
def get_nonce():
    """Generate and return a nonce for DID authentication."""
    nonce = str(uuid.uuid4())
    session['nonce'] = nonce
    session['nonce_timestamp'] = time.time()
    return jsonify({'nonce': nonce})

@app.route('/api/login/traditional', methods=['POST'])
def login_traditional():
    """Handle traditional username/password login."""
    start_time = time.time()
    data = request.get_json()
    
    username = data.get('username')
    password = data.get('password')
    research_session_id = get_or_create_research_session()
    attempt_number = session.get('auth_attempt', 1)
    
    if not username or not password:
        log_auth_attempt(research_session_id, None, 'TRADITIONAL', attempt_number,
                        start_time, False, 'MISSING_CREDENTIALS', 
                        'Username or password missing', request.user_agent.string)
        return jsonify({'success': False, 'error': 'Missing credentials'}), 400
    
    # Verify credentials
    user_id, error_code, error_message = verify_credentials(username, password)
    
    if user_id:
        log_auth_attempt(research_session_id, user_id, 'TRADITIONAL', attempt_number,
                        start_time, True, None, None, request.user_agent.string)
        session['authenticated_user_id'] = user_id
        session['last_auth_method'] = 'TRADITIONAL'
        return jsonify({'success': True, 'redirect': '/education/TRADITIONAL'})
    else:
        log_auth_attempt(research_session_id, None, 'TRADITIONAL', attempt_number,
                        start_time, False, error_code, error_message, 
                        request.user_agent.string)
        return jsonify({'success': False, 'error': error_message}), 401

@app.route('/api/login/did', methods=['POST'])
def login_did():
    """Handle DID authentication via signature verification."""
    start_time = time.time()
    data = request.get_json()
    
    address = data.get('address')
    signature = data.get('signature')
    message = data.get('message')
    research_session_id = get_or_create_research_session()
    attempt_number = session.get('auth_attempt', 1)
    
    if not address or not signature or not message:
        log_auth_attempt(research_session_id, None, 'DID', attempt_number,
                        start_time, False, 'MISSING_PARAMS', 
                        'Address, signature, or message missing', 
                        request.user_agent.string)
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400
    
    # Verify nonce
    if 'nonce' not in session or session['nonce'] != message:
        log_auth_attempt(research_session_id, None, 'DID', attempt_number,
                        start_time, False, 'INVALID_NONCE', 
                        'Nonce mismatch or expired', request.user_agent.string)
        return jsonify({'success': False, 'error': 'Invalid or expired nonce'}), 401
    
    # Check nonce age (max 5 minutes)
    if time.time() - session.get('nonce_timestamp', 0) > 300:
        log_auth_attempt(research_session_id, None, 'DID', attempt_number,
                        start_time, False, 'NONCE_EXPIRED', 
                        'Nonce expired', request.user_agent.string)
        return jsonify({'success': False, 'error': 'Nonce expired. Please try again.'}), 401
    
    # Verify signature
    sig_valid, error_code, error_message = verify_signature(address, message, signature)
    
    if sig_valid:
        user_id, is_new = get_user_by_wallet(address)
        log_auth_attempt(research_session_id, user_id, 'DID', attempt_number,
                        start_time, True, None, None, request.user_agent.string)
        session['authenticated_user_id'] = user_id
        session['last_auth_method'] = 'DID'
        session.pop('nonce', None)
        session.pop('nonce_timestamp', None)
        return jsonify({'success': True, 'redirect': '/education/DID', 'is_new_user': is_new})
    else:
        log_auth_attempt(research_session_id, None, 'DID', attempt_number,
                        start_time, False, error_code, error_message, 
                        request.user_agent.string)
        return jsonify({'success': False, 'error': error_message}), 401

@app.route('/education/<method>')
def education(method):
    """Show educational content about the method just used."""
    if session.get('last_auth_method') != method:
        return redirect(url_for('index'))
    
    session['education_start'] = time.time()
    return render_template('education.html', method=method)

@app.route('/api/education/complete', methods=['POST'])
def complete_education():
    """Log education view completion."""
    data = request.get_json()
    method = data.get('method')
    research_session_id = get_or_create_research_session()
    
    duration = time.time() - session.get('education_start', time.time())
    log_education_view(research_session_id, method, duration)
    
    return jsonify({'success': True, 'redirect': f'/feedback/{method}'})

@app.route('/feedback/<method>')
def feedback_page(method):
    """Show feedback form for the method just used."""
    if session.get('last_auth_method') != method:
        return redirect(url_for('index'))
    
    return render_template('feedback.html', method=method)

@app.route('/api/feedback/submit', methods=['POST'])
def submit_feedback():
    """Handle feedback submission."""
    data = request.get_json()
    method = data.get('method')
    research_session_id = get_or_create_research_session()
    
    save_feedback(
        research_session_id,
        method,
        data.get('ease_of_use'),
        data.get('speed_rating'),
        data.get('security_feeling'),
        data.get('would_use_again'),
        data.get('comments', '')
    )
    
    # Mark method as completed
    completed = session.get('methods_completed', [])
    if method not in completed:
        completed.append(method)
        session['methods_completed'] = completed
    
    # Check if we need to do the other method
    next_method = determine_next_method()
    
    if next_method:
        session['current_step'] = 'auth'
        session['auth_attempt'] = 0
        return jsonify({'success': True, 'redirect': '/authenticate'})
    else:
        return jsonify({'success': True, 'redirect': '/final-feedback'})

@app.route('/final-feedback')
def final_feedback():
    """Show final comparative feedback."""
    if len(session.get('methods_completed', [])) < 2:
        return redirect(url_for('index'))
    
    return render_template('final_feedback.html')

@app.route('/api/final-feedback/submit', methods=['POST'])
def submit_final_feedback():
    """Handle final feedback submission."""
    research_session_id = get_or_create_research_session()
    complete_session(research_session_id)
    
    return jsonify({'success': True, 'redirect': '/thank-you'})

@app.route('/thank-you')
def thank_you():
    """Thank you page."""
    return render_template('thank_you.html')

# =============================================================================
# ADMIN PANEL
# =============================================================================

@app.route('/admin/login')
def admin_login():
    """Admin login page."""
    return render_template('admin_login.html')

@app.route('/admin/auth', methods=['POST'])
def admin_auth():
    """Authenticate admin."""
    password = request.form.get('password')
    if password == ADMIN_PASSWORD:
        session['is_admin'] = True
        return redirect(url_for('admin_dashboard'))
    else:
        return render_template('admin_login.html', error='Invalid password')

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard with analytics."""
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    analytics = get_analytics()
    sessions = get_all_sessions()
    
    return render_template('admin_dashboard.html', 
                         analytics=analytics,
                         sessions=sessions)

@app.route('/admin/clear-data', methods=['POST'])
def admin_clear_data():
    """Clear all research data."""
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    clear_all_data()
    return jsonify({'success': True, 'message': 'All research data cleared'})

@app.route('/admin/logout')
def admin_logout():
    """Logout admin."""
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    init_db()
    create_test_user('test', 'test123')
    
    print("\n" + "="*60)
    print("🔬 AUTHENTICATION RESEARCH PLATFORM")
    print("="*60)
    print("📊 Research Portal: http://127.0.0.1:5000")
    print("🔐 Admin Panel: http://127.0.0.1:5000/admin/login")
    print("   Admin Password: admin123")
    print("="*60)
    print("📝 Test Credentials:")
    print("   Username: test")
    print("   Password: test123")
    print("="*60 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
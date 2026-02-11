from database.db import get_db
from eth_account.messages import encode_defunct
from eth_account import Account

def verify_signature(public_address, message_text, signature):
    """Verify that the signature was created by the wallet address.
    Returns (success, error_code, error_message)."""
    try:
        # Encode the message
        message = encode_defunct(text=message_text)
        
        # Recover the address from the signature
        recovered_address = Account.recover_message(message, signature=signature)
        
        # Compare addresses (case-insensitive)
        if recovered_address.lower() == public_address.lower():
            return True, None, None
        else:
            return False, "ADDRESS_MISMATCH", f"Signature does not match address"
    except Exception as e:
        return False, "SIGNATURE_INVALID", f"Invalid signature format: {str(e)}"

def get_user_by_wallet(wallet_address):
    """Get user by wallet address, or create new user if doesn't exist.
    Returns (user_id, is_new_user)."""
    db = get_db()
    cursor = db.cursor()
    
    # Normalize address to lowercase
    wallet_address = wallet_address.lower()
    
    # Try to find existing user
    cursor.execute('SELECT id FROM users WHERE wallet_address = ?', (wallet_address,))
    user = cursor.fetchone()
    
    if user:
        user_id = user['id']
        db.close()
        return user_id, False
    
    # Auto-register new wallet
    cursor.execute('INSERT INTO users (wallet_address) VALUES (?)', (wallet_address,))
    db.commit()
    user_id = cursor.lastrowid
    db.close()
    
    return user_id, True
// UI Elements
const createBtn = document.getElementById('create-identity');
const signBtn = document.getElementById('sign-challenge');
const deleteBtn = document.getElementById('delete-wallet');
const setupSection = document.getElementById('setup-section');
const loginSection = document.getElementById('login-section');
const walletStatus = document.getElementById('wallet-status');
const addressDisplay = document.getElementById('address-display');
const statusMessage = document.getElementById('status-message');

// Show status message
function showMessage(text, type = 'info') {
    statusMessage.innerHTML = `<div class="message ${type}">${text}</div>`;
    setTimeout(() => {
        statusMessage.innerHTML = '';
    }, 5000);
}

// Update UI based on wallet state
async function updateUI() {
    try {
        const result = await chrome.storage.local.get(['privateKey', 'address']);
        
        if (result.address && result.privateKey) {
            // Wallet exists
            setupSection.classList.add('hidden');
            loginSection.classList.remove('hidden');
            walletStatus.innerHTML = '✅ Wallet active and ready';
            addressDisplay.textContent = result.address;
            addressDisplay.classList.remove('hidden');
        } else {
            // No wallet
            setupSection.classList.remove('hidden');
            loginSection.classList.add('hidden');
            walletStatus.innerHTML = '⚠️ No wallet created yet';
            addressDisplay.classList.add('hidden');
        }
    } catch (error) {
        walletStatus.innerHTML = '❌ Error loading wallet';
        showMessage('Error loading wallet: ' + error.message, 'error');
    }
}

// Create New Identity
createBtn.addEventListener('click', async () => {
    const originalText = document.getElementById('create-btn-text').innerHTML;
    
    try {
        // Show loading
        createBtn.disabled = true;
        document.getElementById('create-btn-text').innerHTML = '<span class="loading"></span> Creating...';
        
        // Generate new wallet
        const wallet = ethers.Wallet.createRandom();
        
        // Store credentials
        await chrome.storage.local.set({
            privateKey: wallet.privateKey,
            address: wallet.address
        });
        
        showMessage('✅ Identity created successfully!', 'success');
        await updateUI();
        
    } catch (error) {
        showMessage('❌ Error: ' + error.message, 'error');
        document.getElementById('create-btn-text').innerHTML = originalText;
        createBtn.disabled = false;
    }
});

// Sign Login Challenge
signBtn.addEventListener('click', async () => {
    const originalText = document.getElementById('sign-btn-text').innerHTML;
    
    try {
        // Show loading
        signBtn.disabled = true;
        document.getElementById('sign-btn-text').innerHTML = '<span class="loading"></span> Signing...';
        
        // Get stored credentials
        const result = await chrome.storage.local.get(['privateKey', 'address']);
        
        if (!result.privateKey || !result.address) {
            throw new Error('No wallet found. Please create one first.');
        }
        
        // Fetch nonce from server
        showMessage('📡 Fetching challenge from server...', 'info');
        const nonceResponse = await fetch('http://127.0.0.1:5000/api/nonce', {
            credentials: 'include'
        });
        
        if (!nonceResponse.ok) {
            throw new Error('Failed to get challenge from server');
        }
        
        const nonceData = await nonceResponse.json();
        const nonce = nonceData.nonce;
        
        // Sign the nonce
        showMessage('✍️ Signing with your wallet...', 'info');
        const wallet = new ethers.Wallet(result.privateKey);
        const signature = await wallet.signMessage(nonce);
        
        // Send to content script
        showMessage('📤 Sending signature to page...', 'info');
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        if (!tab) {
            throw new Error('No active tab found');
        }
        
        await chrome.tabs.sendMessage(tab.id, {
            type: 'DID_AUTH_RESPONSE',
            address: result.address,
            signature: signature,
            message: nonce
        });
        
        showMessage('✅ Authentication sent successfully!', 'success');
        
    } catch (error) {
        showMessage('❌ Error: ' + error.message, 'error');
    } finally {
        signBtn.disabled = false;
        document.getElementById('sign-btn-text').innerHTML = originalText;
    }
});

// Delete Wallet
deleteBtn.addEventListener('click', async () => {
    if (!confirm('Are you sure you want to delete your wallet? This cannot be undone!')) {
        return;
    }
    
    try {
        await chrome.storage.local.clear();
        showMessage('✅ Wallet deleted successfully', 'success');
        await updateUI();
    } catch (error) {
        showMessage('❌ Error: ' + error.message, 'error');
    }
});

// Initialize UI on load
updateUI();
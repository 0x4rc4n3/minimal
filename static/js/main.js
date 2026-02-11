// Check if extension is loaded (for DID method)
let extensionReady = false;

window.addEventListener('message', (event) => {
    if (event.data.type === 'DID_EXTENSION_READY') {
        extensionReady = true;
        console.log('DID Wallet extension detected');
    }
});

// Traditional Login Handler
if (document.getElementById('auth-form')) {
    document.getElementById('auth-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const btnText = document.getElementById('btn-text');
        const resultDiv = document.getElementById('result-message');
        
        btnText.textContent = 'Authenticating...';
        resultDiv.style.display = 'none';
        
        try {
            const response = await fetch('/api/login/traditional', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (data.success) {
                resultDiv.className = 'success';
                resultDiv.textContent = '✓ Authentication successful! Redirecting...';
                resultDiv.style.display = 'block';
                
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1000);
            } else {
                resultDiv.className = 'error';
                resultDiv.textContent = '✗ ' + data.error;
                resultDiv.style.display = 'block';
                btnText.textContent = 'Login';
            }
        } catch (error) {
            resultDiv.className = 'error';
            resultDiv.textContent = '✗ Network error. Please try again.';
            resultDiv.style.display = 'block';
            btnText.textContent = 'Login';
        }
    });
}

// DID Authentication Handler
if (typeof authMethod !== 'undefined' && authMethod === 'DID') {
    const statusIndicator = document.getElementById('status-indicator');
    const resultDiv = document.getElementById('result-message');
    
    // Listen for signature from extension
    window.addEventListener('message', async (event) => {
        if (event.source !== window) return;
        
        if (event.data.type === 'DID_AUTH_RESPONSE' && event.data.source === 'did-wallet-extension') {
            await handleDidAuthentication(event.data);
        }
    });
    
    async function handleDidAuthentication(data) {
        statusIndicator.innerHTML = '<div class="spinner"></div><p>Verifying signature...</p>';
        
        try {
            const response = await fetch('/api/login/did', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    address: data.address,
                    signature: data.signature,
                    message: data.message
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                statusIndicator.style.display = 'none';
                resultDiv.className = 'success';
                resultDiv.textContent = '✓ Authentication successful! Redirecting...';
                resultDiv.style.display = 'block';
                
                setTimeout(() => {
                    window.location.href = result.redirect;
                }, 1000);
            } else {
                statusIndicator.innerHTML = '<p style="color: var(--danger);">✗ Authentication failed. Please try again.</p>';
                resultDiv.className = 'error';
                resultDiv.textContent = '✗ ' + result.error;
                resultDiv.style.display = 'block';
                
                // Reset after 3 seconds
                setTimeout(() => {
                    statusIndicator.innerHTML = '<div class="spinner"></div><p>Waiting for wallet signature...</p>';
                    resultDiv.style.display = 'none';
                }, 3000);
            }
        } catch (error) {
            statusIndicator.innerHTML = '<p style="color: var(--danger);">✗ Network error</p>';
            resultDiv.className = 'error';
            resultDiv.textContent = '✗ Network error. Please try again.';
            resultDiv.style.display = 'block';
            
            setTimeout(() => {
                statusIndicator.innerHTML = '<div class="spinner"></div><p>Waiting for wallet signature...</p>';
                resultDiv.style.display = 'none';
            }, 3000);
        }
    }
    
    // Check extension status after page load
    setTimeout(() => {
        if (!extensionReady) {
            const warning = document.createElement('div');
            warning.className = 'error';
            warning.style.marginTop = '20px';
            warning.innerHTML = `
                <strong>⚠️ Extension Not Detected</strong><br>
                Please make sure the DID Wallet extension is installed and enabled.
            `;
            statusIndicator.appendChild(warning);
        }
    }, 2000);
}
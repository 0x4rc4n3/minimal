// Content script - runs on the research platform page

// Listen for messages from the extension popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'DID_AUTH_RESPONSE') {
        // Forward to page
        window.postMessage({
            type: 'DID_AUTH_RESPONSE',
            address: message.address,
            signature: message.signature,
            message: message.message,
            source: 'did-wallet-extension'
        }, '*');
        
        sendResponse({ success: true });
    }
    return true;
});

// Notify page that extension is loaded
window.postMessage({
    type: 'DID_EXTENSION_READY',
    source: 'did-wallet-extension'
}, '*');
let sessionId = 'user_' + Math.random().toString(36).substr(2, 9);

function toggleChat() {
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.classList.toggle('active');

    // Auto focus input when opening
    if (chatContainer.classList.contains('active')) {
        document.getElementById('userInput').focus();
    }
}

async function sendMessage() {
    const input = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const question = input.value.trim();

    if (!question) return;

    // UI Loading State
    input.disabled = true;
    sendBtn.disabled = true;
    const originalBtnContent = sendBtn.innerHTML;
    sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; // Spinner icon

    addMessage(question, 'user');
    input.value = '';

    try {
        const response = await fetch('http://localhost:5000/api/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                session_id: sessionId
            })
        });

        const data = await response.json();

        if (response.ok) {
            addMessage(data.answer, 'bot');
            updateStatus(`Response: ${data.response_time}s`);
        } else {
            addMessage('Sorry, error occurred.', 'bot');
        }

    } catch (error) {
        addMessage('Cannot connect to server. Is backend running?', 'bot');
    }

    // Restore UI State
    input.disabled = false;
    sendBtn.disabled = false;
    sendBtn.innerHTML = originalBtnContent;
    input.focus();
}

function addMessage(text, sender) {
    const messagesDiv = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Convert Markdown links [text](url) to HTML <a> tags
    const formattedText = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    contentDiv.innerHTML = `<p>${formattedText.replace(/\n/g, '<br>')}</p>`;

    messageDiv.appendChild(contentDiv);
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function updateStatus(text) {
    const statusDiv = document.getElementById('status');
    if (statusDiv) statusDiv.textContent = text;
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

window.onload = function () {
    console.log("LushBot Frontend Loaded");
    // Check backend health silently
    fetch('http://localhost:5000/api/health')
        .then(res => {
            if (res.ok) updateStatus('Use the chat button to ask questions!');
        })
        .catch(err => {
            updateStatus('⚠️ Backend offline');
        });
}
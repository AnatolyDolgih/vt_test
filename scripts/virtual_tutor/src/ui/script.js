const client_id = Date.now()
const wsUrl = `${location.origin.replace(/^http/, 'ws')}/legacy/wss/${client_id}`
let web_socket = new WebSocket(wsUrl);

web_socket.onopen = () => {
    console.log('WebSocket Connection established');
};

web_socket.onmessage = (event) => {
    const response = JSON.parse(event.data);
    console.log(response)
    addMessage(response.content, false);
};

const dialogEditor = document.getElementById('dialogEditor');
const essayEditor = document.getElementById('essayEditor');
const chatMessages = document.getElementById('chatMessages');

function addMessage(message, isUser = true) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'tutor'}`;
    messageDiv.textContent = message;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function submitDialog() {
    const message = dialogEditor.value;
    if (!message.trim()) return;

    addMessage(message, true);
    dialogEditor.value = '';

    try {
        if (web_socket.readyState === WebSocket.OPEN) {
            const data_dialog = {
                type: 'chat',
                content: message,
                timestamp: new Date().toISOString()
            };
            web_socket.send(JSON.stringify(data_dialog));
            console.log(data_dialog.content)
        }
    } catch (error) {
        console.error('Error submitting dialog:', error);
        alert('Error submitting dialog. Please try again.');
    }
}

async function submitEssay() {
    const message = essayEditor.value;
    addMessage(message, true)
    try {
        if (web_socket.readyState === WebSocket.OPEN) {
            const data_essay = {
                type: 'essay',
                content: essayEditor.value,
                timestamp: new Date().toISOString()
            };
            web_socket.send(JSON.stringify(data_essay));
            console.log(data_essay.content)
        }
    } catch (error) {
        console.error('Error submitting essay:', error);
        alert('Error submitting essay. Please try again.');
    }
}

function showSaveAnimation(element) {
    element.parentElement.classList.add('saving');
    setTimeout(() => {
        element.parentElement.classList.remove('saving');
    }, 1000);
}

window.addEventListener('load', () => {
    addMessage('Здравствуйте! Я ваш виртуальный тьютор. Чем могу помочь?', false);
});

dialogEditor.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitDialog();
    }
});

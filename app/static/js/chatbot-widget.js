/**
 * Floating Chatbot Widget
 * Bottom-right chat interface for all dashboard pages
 */

class ChatbotWidget {
  constructor(config = {}) {
    this.llmConfigured = config.llmConfigured || false;
    this.ragConfigured = config.ragConfigured || false;
    this.currentMode = 'agent';
    this.conversations = {
      agent: [],
      chat: [{ role: 'system', content: 'You are a concise, helpful assistant. Answer the user\'s questions clearly.' }],
      rag: []
    };
    this.isSending = false;

    this.init();
  }

  init() {
    this.createWidget();
    this.attachEventListeners();
  }

  createWidget() {
    // Create widget HTML
    const widgetHTML = `
      <!-- Chat Button -->
      <button class="chat-widget-button" id="chatWidgetButton" aria-label="Open chat">
        ✨
      </button>

      <!-- Chat Window -->
      <div class="chat-widget-window" id="chatWidgetWindow">
        <div class="chat-widget-header">
          <div class="chat-widget-header-title">
            <span>✨</span>
            <span>AI Assistant</span>
          </div>
          <button class="chat-widget-close" id="chatWidgetClose" aria-label="Close chat">
            ×
          </button>
        </div>

        <div class="chat-widget-mode">
          <label for="chatWidgetMode" style="font-weight: 600; color: var(--text-muted);">Mode:</label>
          <select id="chatWidgetMode" ${!this.llmConfigured ? 'disabled' : ''}>
            <option value="agent">Smart Agent (Tools)</option>
            <option value="chat">General Chat</option>
            <option value="rag" ${!this.ragConfigured ? 'disabled' : ''}>Knowledge Base (RAG)</option>
          </select>
        </div>

        <div class="chat-widget-body" id="chatWidgetBody">
          <div class="chat-widget-message assistant">
            Hi! I'm the Magdeburg Smart Agent. Ask me about weather, accidents, transit, trees, cafes, or any Magdeburg data.
          </div>
        </div>

        <div class="chat-widget-footer">
          <div class="chat-widget-status" id="chatWidgetStatus">
            ${this.llmConfigured ? 'Ready to chat!' : 'Chat not configured. Check SERVER_URL and SERVER_TOKEN.'}
          </div>
          <div class="chat-widget-input-wrapper">
            <textarea
              id="chatWidgetInput"
              class="chat-widget-input"
              placeholder="Ask a question..."
              rows="1"
              ${!this.llmConfigured ? 'disabled' : ''}
            ></textarea>
            <button
              id="chatWidgetSend"
              class="chat-widget-send"
              ${!this.llmConfigured ? 'disabled' : ''}
            >
              Send
            </button>
          </div>
        </div>
      </div>
    `;

    // Append to body
    const container = document.createElement('div');
    container.innerHTML = widgetHTML;
    document.body.appendChild(container);

    // Get references
    this.button = document.getElementById('chatWidgetButton');
    this.window = document.getElementById('chatWidgetWindow');
    this.closeBtn = document.getElementById('chatWidgetClose');
    this.body = document.getElementById('chatWidgetBody');
    this.input = document.getElementById('chatWidgetInput');
    this.sendBtn = document.getElementById('chatWidgetSend');
    this.status = document.getElementById('chatWidgetStatus');
    this.modeSelect = document.getElementById('chatWidgetMode');
  }

  attachEventListeners() {
    // Open chat
    this.button.addEventListener('click', () => this.openChat());

    // Close chat
    this.closeBtn.addEventListener('click', () => this.closeChat());

    // Send message
    this.sendBtn.addEventListener('click', () => this.sendMessage());

    // Enter to send (Shift+Enter for new line)
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Mode change
    this.modeSelect.addEventListener('change', () => {
      this.currentMode = this.modeSelect.value;
      this.renderMessages();
      this.updateStatus();
    });

    // Auto-resize textarea
    this.input.addEventListener('input', () => {
      this.input.style.height = 'auto';
      this.input.style.height = Math.min(this.input.scrollHeight, 100) + 'px';
    });
  }

  openChat() {
    this.window.classList.add('open');
    this.button.classList.add('open');
    this.input.focus();
  }

  closeChat() {
    this.window.classList.remove('open');
    this.button.classList.remove('open');
  }

  renderMessages() {
    const messages = this.conversations[this.currentMode].filter(m => m.role !== 'system');

    if (messages.length === 0) {
      this.body.innerHTML = `
        <div class="chat-widget-message assistant">
          ${this.getGreeting()}
        </div>
      `;
    } else {
      this.body.innerHTML = messages.map(msg => `
        <div class="chat-widget-message ${msg.role}">
          ${msg.content}
        </div>
      `).join('');
    }

    // Scroll to bottom
    this.body.scrollTop = this.body.scrollHeight;
  }

  getGreeting() {
    const greetings = {
      agent: 'Hi! I\'m the Magdeburg Smart Agent. Ask me about weather, accidents, transit, trees, cafes, or any Magdeburg data.',
      chat: 'Hi! Ask me anything and I will respond here.',
      rag: 'Hi! Ask about the indexed Magdeburg sources and I will answer with retrieval-backed context.'
    };
    return greetings[this.currentMode];
  }

  addMessage(role, content) {
    const messageEl = document.createElement('div');
    messageEl.className = `chat-widget-message ${role}`;
    messageEl.textContent = content;
    this.body.appendChild(messageEl);
    this.body.scrollTop = this.body.scrollHeight;
  }

  updateStatus() {
    const statusTexts = {
      agent: 'Smart Agent is ready. I can fetch live weather, transit, accident data, and more.',
      chat: 'General chat is ready. Keep prompts concise.',
      rag: 'Knowledge mode is ready. I will search indexed sources before answering.'
    };

    if (!this.llmConfigured) {
      this.status.textContent = 'Chat not configured. Check SERVER_URL and SERVER_TOKEN.';
      this.status.classList.add('warning');
    } else if (this.currentMode === 'rag' && !this.ragConfigured) {
      this.status.textContent = 'RAG mode not configured. Check embedding and Qdrant settings.';
      this.status.classList.add('warning');
    } else {
      this.status.textContent = statusTexts[this.currentMode];
      this.status.classList.remove('warning');
    }
  }

  async sendMessage() {
    const message = this.input.value.trim();
    if (!message || this.isSending) return;

    // Add user message
    this.conversations[this.currentMode].push({ role: 'user', content: message });
    this.addMessage('user', message);
    this.input.value = '';
    this.input.style.height = 'auto';

    // Set loading state
    this.isSending = true;
    this.sendBtn.disabled = true;
    this.input.disabled = true;
    this.sendBtn.textContent = '...';
    this.status.textContent = this.currentMode === 'agent'
      ? 'Agent is thinking and calling tools...'
      : 'Waiting for response...';

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: this.conversations[this.currentMode],
          mode: this.currentMode
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Request failed');
      }

      // Add assistant response
      this.conversations[this.currentMode].push({ role: 'assistant', content: data.response });
      this.addMessage('assistant', data.response);
      this.updateStatus();

    } catch (error) {
      console.error('Chat error:', error);
      this.status.textContent = error.message || 'Something went wrong. Please try again.';
      this.status.classList.add('warning');

      // Remove the user message that failed
      this.conversations[this.currentMode].pop();
      this.renderMessages();
    } finally {
      this.isSending = false;
      this.sendBtn.disabled = false;
      this.input.disabled = false;
      this.sendBtn.textContent = 'Send';
      this.input.focus();
    }
  }
}

// Initialize widget when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Get config from page
  const chatConfig = window.chatbotConfig || {
    llmConfigured: false,
    ragConfigured: false
  };

  new ChatbotWidget(chatConfig);
});

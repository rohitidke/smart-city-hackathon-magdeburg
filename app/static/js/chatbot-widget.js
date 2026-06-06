/**
 * Floating Chatbot Widget
 * Bottom-right chat interface for all dashboard pages
 */

class ChatbotWidget {
  constructor(config = {}) {
    this.llmConfigured = config.llmConfigured || false;
    this.ragConfigured = config.ragConfigured || false;
    this.currentMode = 'agent';
    this.isMaximized = localStorage.getItem('chatWidgetMaximized') === 'true';
    this.modeSuggestions = {
      agent: [
        "What's the weather in Magdeburg today?",
        'How many people live in Magdeburg?',
        'How has public transport usage changed in Magdeburg?'
      ],
      rag: []
    };
    this.conversations = {
      agent: [],
      rag: []
    };
    this.isSending = false;

    this.init();
  }

  init() {
    this.createWidget();
    this.attachEventListeners();
    this.renderMessages();
    this.updateStatus();
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
            <span>City AI Agent</span>
          </div>
          <div class="chat-widget-header-actions">
            <button class="chat-widget-header-btn" id="chatWidgetMaximize" aria-label="Maximize chat" title="Maximize chat">
              ⛶
            </button>
            <button class="chat-widget-close" id="chatWidgetClose" aria-label="Close chat">
              ×
            </button>
          </div>
        </div>

        <div class="chat-widget-mode">
          <label for="chatWidgetMode" style="font-weight: 600; color: var(--text-muted);">Mode:</label>
          <select id="chatWidgetMode" ${!this.llmConfigured ? 'disabled' : ''}>
            <option value="agent">Smart Agent (Tools)</option>
            <option value="rag" ${!this.ragConfigured ? 'disabled' : ''}>Knowledge Base (RAG)</option>
          </select>
        </div>

        <div class="chat-widget-body" id="chatWidgetBody">
          <div class="chat-widget-assistant-stack">
            <div class="chat-widget-message assistant">
              <span class="chat-widget-message-icon">🤖</span>
              <div class="chat-widget-message-body">
                <span class="chat-widget-message-content">Hi! I'm the Magdeburg Smart Agent. Ask me about weather, air quality, transit, rents, healthcare, mobility, cafes, or any Magdeburg data.</span>
              </div>
            </div>
            <div class="chat-widget-suggestions">
              <button class="chat-widget-suggestion" type="button">What's the weather in Magdeburg today?</button>
              <button class="chat-widget-suggestion" type="button">How many people live in Magdeburg?</button>
              <button class="chat-widget-suggestion" type="button">How has public transport usage changed in Magdeburg?</button>
            </div>
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
    this.maximizeBtn = document.getElementById('chatWidgetMaximize');
    this.body = document.getElementById('chatWidgetBody');
    this.input = document.getElementById('chatWidgetInput');
    this.sendBtn = document.getElementById('chatWidgetSend');
    this.status = document.getElementById('chatWidgetStatus');
    this.modeSelect = document.getElementById('chatWidgetMode');
    this.updateWindowState();
  }

  attachEventListeners() {
    // Open chat
    this.button.addEventListener('click', () => this.openChat());

    // Close chat
    this.closeBtn.addEventListener('click', () => this.closeChat());

    // Maximize chat
    this.maximizeBtn.addEventListener('click', () => this.toggleMaximize());

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

  toggleMaximize() {
    this.isMaximized = !this.isMaximized;
    localStorage.setItem('chatWidgetMaximized', String(this.isMaximized));
    this.updateWindowState();
  }

  updateWindowState() {
    this.window.classList.toggle('maximized', this.isMaximized);
    this.maximizeBtn.textContent = this.isMaximized ? '❐' : '⛶';
    this.maximizeBtn.setAttribute('aria-label', this.isMaximized ? 'Restore chat size' : 'Maximize chat');
    this.maximizeBtn.setAttribute('title', this.isMaximized ? 'Restore chat size' : 'Maximize chat');
  }

  renderMessages() {
    const messages = this.conversations[this.currentMode].filter(m => m.role !== 'system');
    this.body.innerHTML = '';

    if (messages.length === 0) {
      this.addMessage('assistant', this.getGreeting(), { suggestions: this.modeSuggestions[this.currentMode] });
    } else {
      messages.forEach((msg) => this.addMessage(msg.role, msg.content));
    }

    // Scroll to bottom
    this.body.scrollTop = this.body.scrollHeight;
  }

  getGreeting() {
    const greetings = {
      agent: 'Hi! I\'m the Magdeburg Smart Agent. Ask me about weather, air quality, transit, rents, healthcare, mobility, cafes, or any Magdeburg data.',
      rag: 'Hi! Ask about the indexed Magdeburg sources and I will answer with retrieval-backed context.'
    };
    return greetings[this.currentMode];
  }

  escapeHtml(value) {
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  renderInlineMarkdown(text) {
    let html = this.escapeHtml(text);
    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,!?:;]|$)/g, '$1<em>$2</em>');
    return html;
  }

  renderMarkdown(text) {
    const lines = text.replace(/\r\n/g, '\n').split('\n');
    const blocks = [];
    let paragraph = [];
    let listItems = [];
    let listType = null;
    let codeLines = [];
    let inCodeBlock = false;

    const flushParagraph = () => {
      if (!paragraph.length) return;
      blocks.push(`<p>${paragraph.map((line) => this.renderInlineMarkdown(line)).join('<br>')}</p>`);
      paragraph = [];
    };

    const flushList = () => {
      if (!listItems.length || !listType) return;
      const tag = 'ul';
      blocks.push(`<${tag}>${listItems.map((item) => `<li>${item.split('\n').map((line) => this.renderInlineMarkdown(line)).join('<br>')}</li>`).join('')}</${tag}>`);
      listItems = [];
      listType = null;
    };

    const flushCodeBlock = () => {
      if (!codeLines.length) return;
      blocks.push(`<pre><code>${this.escapeHtml(codeLines.join('\n'))}</code></pre>`);
      codeLines = [];
    };

    for (const rawLine of lines) {
      const line = rawLine.trimEnd();

      if (line.trim().startsWith('```')) {
        flushParagraph();
        flushList();
        if (inCodeBlock) {
          flushCodeBlock();
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
        }
        continue;
      }

      if (inCodeBlock) {
        codeLines.push(rawLine);
        continue;
      }

      if (!line.trim()) {
        flushParagraph();
        flushList();
        continue;
      }

      const headingMatch = line.match(/^(#{1,3})\s+(.*)$/);
      if (headingMatch) {
        flushParagraph();
        flushList();
        const level = headingMatch[1].length;
        blocks.push(`<h${level}>${this.renderInlineMarkdown(headingMatch[2])}</h${level}>`);
        continue;
      }

      const blockquoteMatch = line.match(/^>\s?(.*)$/);
      if (blockquoteMatch) {
        flushParagraph();
        flushList();
        blocks.push(`<blockquote>${this.renderInlineMarkdown(blockquoteMatch[1])}</blockquote>`);
        continue;
      }

      const unorderedMatch = line.match(/^\s*[-*]\s+(.*)$/);
      if (unorderedMatch) {
        flushParagraph();
        if (listType && listType !== 'ul') flushList();
        listType = 'ul';
        listItems.push(unorderedMatch[1]);
        continue;
      }

      const orderedMatch = line.match(/^\s*\d+\.\s*(.*)$/);
      if (orderedMatch && orderedMatch[1]) {
        flushParagraph();
        if (listType && listType !== 'ul') flushList();
        listType = 'ul';
        listItems.push(orderedMatch[1]);
        continue;
      }

      if (listItems.length) {
        listItems[listItems.length - 1] += `\n${line.trim()}`;
        continue;
      }

      paragraph.push(line);
    }

    flushParagraph();
    flushList();
    flushCodeBlock();

    return blocks.join('');
  }

  async sendSuggestedMessage(prompt) {
    if (!prompt || this.isSending || this.sendBtn.disabled || this.input.disabled) return;
    this.input.value = prompt;
    await this.sendMessage();
  }

  buildSuggestionRow(suggestions = []) {
    if (!suggestions.length) return null;

    const row = document.createElement('div');
    row.className = 'chat-widget-suggestions';

    for (const suggestion of suggestions) {
      const button = document.createElement('button');
      button.className = 'chat-widget-suggestion';
      button.type = 'button';
      button.textContent = suggestion;
      button.addEventListener('click', async () => {
        await this.sendSuggestedMessage(suggestion);
      });
      row.appendChild(button);
    }

    return row;
  }

  addMessage(role, content, options = {}) {
    if (role === 'assistant') {
      const stackEl = document.createElement('div');
      stackEl.className = 'chat-widget-assistant-stack';
      const messageEl = document.createElement('div');
      messageEl.className = `chat-widget-message ${role}`;
      const iconEl = document.createElement('span');
      iconEl.className = 'chat-widget-message-icon';
      iconEl.textContent = '🤖';
      messageEl.appendChild(iconEl);

      const bodyEl = document.createElement('div');
      bodyEl.className = 'chat-widget-message-body';
      const contentEl = document.createElement('span');
      contentEl.className = 'chat-widget-message-content';
      contentEl.innerHTML = this.renderMarkdown(content);
      bodyEl.appendChild(contentEl);
      messageEl.appendChild(bodyEl);

      const suggestionsEl = this.buildSuggestionRow(options.suggestions || []);
      if (suggestionsEl) {
        stackEl.appendChild(messageEl);
        stackEl.appendChild(suggestionsEl);
      } else {
        stackEl.appendChild(messageEl);
      }
      this.body.appendChild(stackEl);
      this.body.scrollTop = this.body.scrollHeight;
      return;
    } else {
      const messageEl = document.createElement('div');
      messageEl.className = `chat-widget-message ${role}`;
      const contentEl = document.createElement('span');
      contentEl.className = 'chat-widget-message-content';
      contentEl.textContent = content;
      messageEl.appendChild(contentEl);
      this.body.appendChild(messageEl);
      this.body.scrollTop = this.body.scrollHeight;
    }
  }

  updateStatus() {
    const statusTexts = {
      agent: 'Smart Agent is ready. I can fetch live weather, transit, cafe, and tree data.',
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

/**
 * Google Gemini Web Chatbot - Frontend Application Logic
 * Supports Gemini 3.8 Flash & Gemini 3.7 Flash with real-time SSE streaming
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const mainWorkspace = document.getElementById('mainWorkspace');
  const welcomeContainer = document.getElementById('welcomeContainer');
  const chatStreamContainer = document.getElementById('chatStreamContainer');
  const messagesWrapper = document.getElementById('messagesWrapper');
  
  const promptInput = document.getElementById('promptInput');
  const sendBtn = document.getElementById('sendBtn');
  const attachBtn = document.getElementById('attachBtn');
  const fileInput = document.getElementById('fileInput');
  const attachmentPreview = document.getElementById('attachmentPreview');
  const previewImg = document.getElementById('previewImg');
  const removeAttachmentBtn = document.getElementById('removeAttachmentBtn');
  
  const modelDropdownContainer = document.querySelector('.model-dropdown-container');
  const modelSelectBtn = document.getElementById('modelSelectBtn');
  const currentModelName = document.getElementById('currentModelName');
  const currentModelBadge = document.getElementById('currentModelBadge');
  const modelInfoLabel = document.getElementById('modelInfoLabel');
  const optionGemini38 = document.getElementById('optionGemini38');
  const optionGemini37 = document.getElementById('optionGemini37');
  const optionGemini3Preview = document.getElementById('optionGemini3Preview');
  
  const searchToggleBtn = document.getElementById('searchToggleBtn');
  const micBtn = document.getElementById('micBtn');
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');
  const newChatBtn = document.getElementById('newChatBtn');
  const chatHistoryList = document.getElementById('chatHistoryList');
  
  const usernameText = document.getElementById('usernameText');
  const userInitial = document.getElementById('userInitial');
  const userProfileBtn = document.getElementById('userProfileBtn');
  const nameModalOverlay = document.getElementById('nameModalOverlay');
  const nameInput = document.getElementById('nameInput');
  const cancelNameBtn = document.getElementById('cancelNameBtn');
  const saveNameBtn = document.getElementById('saveNameBtn');

  // Application State
  let currentModel = localStorage.getItem('gemini_selected_model') || 'gemini-3.8-flash';
  let isWebSearchEnabled = localStorage.getItem('gemini_web_search') !== 'false';
  let userName = localStorage.getItem('gemini_user_name') || '10';
  let conversations = JSON.parse(localStorage.getItem('gemini_conversations') || '[]');
  let currentConvId = null;
  let currentAttachedImage = null; // { mimeType: '', data: '' }
  let isGenerating = false;
  let speechRecognition = null;
  let isListening = false;

  // Initialize UI with State
  initUser();
  initModel();
  initWebSearchToggle();
  initConversations();
  initSpeechRecognition();

  // =========================================================================
  // User Profile / Nickname Setup
  // =========================================================================
  function initUser() {
    usernameText.textContent = userName;
    userInitial.textContent = userName.slice(0, 2);
  }

  function openNameModal() {
    nameInput.value = userName;
    nameModalOverlay.style.display = 'flex';
    nameInput.focus();
  }

  function closeNameModal() {
    nameModalOverlay.style.display = 'none';
  }

  usernameText.addEventListener('click', openNameModal);
  userProfileBtn.addEventListener('click', openNameModal);
  cancelNameBtn.addEventListener('click', closeNameModal);

  saveNameBtn.addEventListener('click', () => {
    const newName = nameInput.value.trim();
    if (newName) {
      userName = newName;
      localStorage.setItem('gemini_user_name', userName);
      initUser();
    }
    closeNameModal();
  });

  nameModalOverlay.addEventListener('click', (e) => {
    if (e.target === nameModalOverlay) closeNameModal();
  });

  // =========================================================================
  // Model Selection Setup
  // =========================================================================
  function initModel() {
    updateModelUI(currentModel);
  }

  function updateModelUI(modelId) {
    currentModel = modelId;
    localStorage.setItem('gemini_selected_model', modelId);

    optionGemini38.classList.remove('selected');
    optionGemini37.classList.remove('selected');
    if (optionGemini3Preview) optionGemini3Preview.classList.remove('selected');

    if (modelId === 'gemini-3.7-flash') {
      currentModelName.textContent = 'Flash 3.7';
      currentModelBadge.textContent = '3.7 Flash';
      modelInfoLabel.textContent = 'Gemini 3.7 Flash 활성화';
      optionGemini37.classList.add('selected');
    } else if (modelId === 'gemini-3-flash-preview') {
      currentModelName.textContent = '3 Preview';
      currentModelBadge.textContent = '3 Preview';
      modelInfoLabel.textContent = 'Gemini 3 Preview 활성화';
      if (optionGemini3Preview) optionGemini3Preview.classList.add('selected');
    } else {
      currentModelName.textContent = 'Flash';
      currentModelBadge.textContent = '3.8 Flash';
      modelInfoLabel.textContent = 'Gemini 3.8 Flash 활성화';
      optionGemini38.classList.add('selected');
    }
  }

  modelSelectBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    modelDropdownContainer.classList.toggle('active');
  });

  document.addEventListener('click', (e) => {
    if (!modelDropdownContainer.contains(e.target)) {
      modelDropdownContainer.classList.remove('active');
    }
  });

  optionGemini38.addEventListener('click', () => {
    updateModelUI('gemini-3.8-flash');
    modelDropdownContainer.classList.remove('active');
  });

  optionGemini37.addEventListener('click', () => {
    updateModelUI('gemini-3.7-flash');
    modelDropdownContainer.classList.remove('active');
  });

  if (optionGemini3Preview) {
    optionGemini3Preview.addEventListener('click', () => {
      updateModelUI('gemini-3-flash-preview');
      modelDropdownContainer.classList.remove('active');
    });
  }

  // =========================================================================
  // Web Search Grounding Toggle
  // =========================================================================
  function initWebSearchToggle() {
    if (!searchToggleBtn) return;
    updateSearchToggleUI();

    searchToggleBtn.addEventListener('click', () => {
      isWebSearchEnabled = !isWebSearchEnabled;
      localStorage.setItem('gemini_web_search', isWebSearchEnabled);
      updateSearchToggleUI();
    });
  }

  function updateSearchToggleUI() {
    if (!searchToggleBtn) return;
    if (isWebSearchEnabled) {
      searchToggleBtn.classList.add('active');
      searchToggleBtn.title = '실시간 인터넷 검색 활성화됨 (클릭 시 끄기)';
    } else {
      searchToggleBtn.classList.remove('active');
      searchToggleBtn.title = '인터넷 검색 꺼짐 (클릭 시 켜기)';
    }
  }

  // =========================================================================
  // Sidebar & Chat History
  // =========================================================================
  function toggleSidebar() {
    sidebar.classList.toggle('open');
    sidebarBackdrop.classList.toggle('active');
  }

  sidebarToggle.addEventListener('click', toggleSidebar);
  sidebarBackdrop.addEventListener('click', toggleSidebar);

  newChatBtn.addEventListener('click', () => {
    startNewChat();
    if (window.innerWidth <= 768) {
      toggleSidebar();
    }
  });

  function startNewChat() {
    currentConvId = null;
    currentAttachedImage = null;
    hideAttachmentPreview();
    messagesWrapper.innerHTML = '';
    mainWorkspace.classList.remove('in-chat');
    promptInput.value = '';
    updateSendBtnState();
    promptInput.focus();
    renderConversationList();
  }

  function saveConversations() {
    localStorage.setItem('gemini_conversations', JSON.stringify(conversations));
    renderConversationList();
  }

  function initConversations() {
    renderConversationList();
  }

  function renderConversationList() {
    chatHistoryList.innerHTML = '';
    if (conversations.length === 0) {
      const emptyDiv = document.createElement('div');
      emptyDiv.style.padding = '14px 16px';
      emptyDiv.style.fontSize = '12px';
      emptyDiv.style.color = 'var(--text-tertiary)';
      emptyDiv.textContent = '저장된 대화 기록이 없습니다.';
      chatHistoryList.appendChild(emptyDiv);
      return;
    }

    conversations.forEach((conv) => {
      const item = document.createElement('div');
      item.className = `history-item ${conv.id === currentConvId ? 'active' : ''}`;
      
      const titleSpan = document.createElement('span');
      titleSpan.className = 'history-title';
      titleSpan.textContent = conv.title || '새 대화';
      item.appendChild(titleSpan);

      const actions = document.createElement('div');
      actions.className = 'history-actions';

      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'history-btn';
      deleteBtn.title = '삭제';
      deleteBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
          <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
        </svg>
      `;
      deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteConversation(conv.id);
      });

      actions.appendChild(deleteBtn);
      item.appendChild(actions);

      item.addEventListener('click', () => {
        loadConversation(conv.id);
        if (window.innerWidth <= 768) {
          toggleSidebar();
        }
      });

      chatHistoryList.appendChild(item);
    });
  }

  function loadConversation(id) {
    const conv = conversations.find(c => c.id === id);
    if (!conv) return;

    currentConvId = id;
    mainWorkspace.classList.add('in-chat');
    messagesWrapper.innerHTML = '';

    conv.messages.forEach(msg => {
      if (msg.role === 'user') {
        appendUserMessage(msg.content, msg.image ? msg.image.data : null);
      } else {
        const row = appendGeminiMessage(msg.model || currentModel);
        const bubble = row.querySelector('.message-bubble');
        bubble.innerHTML = renderMarkdown(msg.content);
        if (msg.grounding) {
          appendGroundingSection(row, msg.grounding);
        }
        attachActionButtons(row, msg.content);
      }
    });

    scrollToBottom();
    renderConversationList();
  }

  function deleteConversation(id) {
    conversations = conversations.filter(c => c.id !== id);
    if (currentConvId === id) {
      startNewChat();
    } else {
      saveConversations();
    }
  }

  // =========================================================================
  // Prompt Input & Auto-Resizing
  // =========================================================================
  promptInput.addEventListener('input', () => {
    promptInput.style.height = 'auto';
    promptInput.style.height = Math.min(promptInput.scrollHeight, 160) + 'px';
    updateSendBtnState();
  });

  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled && !isGenerating) {
        sendMessage();
      }
    }
  });

  function updateSendBtnState() {
    const text = promptInput.value.trim();
    sendBtn.disabled = (!text && !currentAttachedImage) || isGenerating;
  }

  // =========================================================================
  // Image Attachment Handlers (Multimodal)
  // =========================================================================
  attachBtn.addEventListener('click', () => {
    fileInput.click();
  });

  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file && file.type.startsWith('image/')) {
      handleImageFile(file);
    }
  });

  function handleImageFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target.result;
      currentAttachedImage = {
        mimeType: file.type,
        data: dataUrl
      };
      previewImg.src = dataUrl;
      attachmentPreview.style.display = 'flex';
      updateSendBtnState();
    };
    reader.readAsDataURL(file);
  }

  removeAttachmentBtn.addEventListener('click', () => {
    hideAttachmentPreview();
    updateSendBtnState();
  });

  function hideAttachmentPreview() {
    currentAttachedImage = null;
    attachmentPreview.style.display = 'none';
    previewImg.src = '';
    fileInput.value = '';
  }

  // Drag and drop image onto prompt box
  const promptPillBox = document.getElementById('promptPillBox');
  ['dragenter', 'dragover'].forEach(eventName => {
    promptPillBox.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      promptPillBox.style.borderColor = 'var(--accent-blue)';
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    promptPillBox.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      promptPillBox.style.borderColor = '';
    }, false);
  });

  promptPillBox.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const file = dt.files[0];
    if (file && file.type.startsWith('image/')) {
      handleImageFile(file);
    }
  });

  // =========================================================================
  // Web Speech Recognition (Mic Input)
  // =========================================================================
  function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      micBtn.title = '이 브라우저는 음성 인식을 지원하지 않습니다.';
      return;
    }

    speechRecognition = new SpeechRecognition();
    speechRecognition.lang = 'ko-KR';
    speechRecognition.continuous = false;
    speechRecognition.interimResults = false;

    speechRecognition.onstart = () => {
      isListening = true;
      micBtn.classList.add('listening');
    };

    speechRecognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      if (promptInput.value) {
        promptInput.value += ' ' + transcript;
      } else {
        promptInput.value = transcript;
      }
      promptInput.dispatchEvent(new Event('input'));
    };

    speechRecognition.onerror = () => {
      isListening = false;
      micBtn.classList.remove('listening');
    };

    speechRecognition.onend = () => {
      isListening = false;
      micBtn.classList.remove('listening');
    };

    micBtn.addEventListener('click', () => {
      if (!isListening) {
        speechRecognition.start();
      } else {
        speechRecognition.stop();
      }
    });
  }

  // =========================================================================
  // Sending Messages & Streaming
  // =========================================================================
  sendBtn.addEventListener('click', () => {
    if (!sendBtn.disabled && !isGenerating) {
      sendMessage();
    }
  });

  async function sendMessage(overridePrompt = null) {
    const promptText = overridePrompt !== null ? overridePrompt : promptInput.value.trim();
    if (!promptText && !currentAttachedImage) return;

    const attachedImgToSend = currentAttachedImage;
    
    // Clear input & reset preview
    promptInput.value = '';
    promptInput.style.height = 'auto';
    hideAttachmentPreview();
    updateSendBtnState();

    // Transition to chat layout
    mainWorkspace.classList.add('in-chat');

    // Create or retrieve active conversation
    if (!currentConvId) {
      currentConvId = `conv_${Date.now()}`;
      conversations.unshift({
        id: currentConvId,
        title: promptText ? (promptText.length > 25 ? promptText.slice(0, 25) + '...' : promptText) : '이미지 질문',
        model: currentModel,
        messages: []
      });
    }

    const currentConv = conversations.find(c => c.id === currentConvId);

    // Append User Message to UI
    appendUserMessage(promptText, attachedImgToSend ? attachedImgToSend.data : null);
    currentConv.messages.push({
      role: 'user',
      content: promptText,
      image: attachedImgToSend
    });
    saveConversations();
    scrollToBottom();

    // Append Assistant Message Placeholder
    const geminiRow = appendGeminiMessage(currentModel);
    const bubble = geminiRow.querySelector('.message-bubble');
    const cursor = document.createElement('span');
    cursor.className = 'typing-cursor';
    bubble.appendChild(cursor);
    scrollToBottom();

    isGenerating = true;
    updateSendBtnState();

    // Prepare message payload for API
    const apiMessages = currentConv.messages.map(m => ({
      role: m.role,
      content: m.content,
      image: m.image
    }));

    let fullResponseText = '';
    const groundingData = { queries: [], sources: [] };

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: currentModel,
          messages: apiMessages,
          webSearch: isWebSearchEnabled
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status} 요청 오류`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep last incomplete line in buffer

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;

          const dataContent = trimmed.replace(/^data:\s*/, '');
          if (dataContent === '[DONE]') {
            break;
          }

          try {
            const parsed = JSON.parse(dataContent);
            if (parsed.error) {
              throw new Error(parsed.error);
            }
            if (parsed.grounding) {
              if (parsed.grounding.queries) {
                groundingData.queries = Array.from(new Set([...groundingData.queries, ...parsed.grounding.queries]));
              }
              if (parsed.grounding.sources) {
                parsed.grounding.sources.forEach(s => {
                  if (!groundingData.sources.some(existing => existing.uri === s.uri)) {
                    groundingData.sources.push(s);
                  }
                });
              }
            }
            if (parsed.text) {
              fullResponseText += parsed.text;
              bubble.innerHTML = renderMarkdown(fullResponseText) + '<span class="typing-cursor"></span>';
              scrollToBottom();
            }
          } catch (e) {
            if (e.message !== 'Unexpected end of JSON input') {
              console.warn('Chunk parsing issue:', e);
            }
          }
        }
      }

      // Streaming finished
      bubble.innerHTML = renderMarkdown(fullResponseText);
      if (groundingData.sources.length > 0 || groundingData.queries.length > 0) {
        appendGroundingSection(geminiRow, groundingData);
      }
      currentConv.messages.push({
        role: 'model',
        model: currentModel,
        content: fullResponseText,
        grounding: (groundingData.sources.length > 0 || groundingData.queries.length > 0) ? groundingData : null
      });
      saveConversations();
      attachActionButtons(geminiRow, fullResponseText, promptText);

    } catch (err) {
      console.error('Chat error:', err);
      bubble.innerHTML = `<span style="color: #ea4335;">오류가 발생했습니다: ${escapeHtml(err.message)}</span>`;
    } finally {
      isGenerating = false;
      updateSendBtnState();
      scrollToBottom();
    }
  }

  // =========================================================================
  // DOM Message Appenders
  // =========================================================================
  function appendUserMessage(text, imageDataUrl) {
    const row = document.createElement('div');
    row.className = 'message-row user';

    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';

    if (imageDataUrl) {
      const img = document.createElement('img');
      img.className = 'message-image-thumb';
      img.src = imageDataUrl;
      wrapper.appendChild(img);
    }

    if (text) {
      const bubble = document.createElement('div');
      bubble.className = 'message-bubble';
      bubble.textContent = text;
      wrapper.appendChild(bubble);
    }

    row.appendChild(wrapper);
    messagesWrapper.appendChild(row);
    return row;
  }

  function appendGeminiMessage(modelId) {
    const row = document.createElement('div');
    row.className = 'message-row gemini';

    // Sparkle Avatar
    const avatar = document.createElement('div');
    avatar.className = 'gemini-avatar-sparkle';
    avatar.innerHTML = `
      <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
        <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z"/>
      </svg>
    `;
    row.appendChild(avatar);

    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';

    // Model label
    const modelLabel = document.createElement('div');
    modelLabel.className = 'gemini-model-label';
    const modelName = modelId === 'gemini-3.7-flash' ? 'Gemini 3.7 Flash' : 'Gemini 3.8 Flash';
    modelLabel.innerHTML = `<span>${modelName}</span>`;
    wrapper.appendChild(modelLabel);

    // Message Bubble
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    wrapper.appendChild(bubble);

    row.appendChild(wrapper);
    messagesWrapper.appendChild(row);
    return row;
  }

  function appendGroundingSection(row, groundingData) {
    if (!groundingData) return;
    const wrapper = row.querySelector('.message-content-wrapper');
    if (!wrapper) return;

    const existing = wrapper.querySelector('.grounding-sources-section');
    if (existing) existing.remove();

    const sources = groundingData.sources || [];
    const queries = groundingData.queries || [];
    if (sources.length === 0 && queries.length === 0) return;

    const section = document.createElement('div');
    section.className = 'grounding-sources-section';

    const header = document.createElement('div');
    header.className = 'grounding-header';
    header.innerHTML = `
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="2" y1="12" x2="22" y2="12"></line>
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
      </svg>
      <span>참조된 실시간 웹 정보 (${sources.length}개 출처)</span>
    `;
    section.appendChild(header);

    if (queries.length > 0) {
      const queriesRow = document.createElement('div');
      queriesRow.className = 'grounding-queries-row';
      queries.forEach(q => {
        const chip = document.createElement('span');
        chip.className = 'grounding-query-chip';
        chip.textContent = `🔍 ${q}`;
        queriesRow.appendChild(chip);
      });
      section.appendChild(queriesRow);
    }

    if (sources.length > 0) {
      const sourcesList = document.createElement('div');
      sourcesList.className = 'grounding-sources-list';
      sources.forEach(source => {
        const a = document.createElement('a');
        a.className = 'grounding-source-card';
        a.href = source.uri;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.title = source.title;

        let domain = '';
        try {
          domain = new URL(source.uri).hostname.replace('www.', '');
        } catch (e) {
          domain = '웹 출처';
        }

        a.innerHTML = `
          <svg class="source-icon" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
          </svg>
          <span class="source-title">${escapeHtml(source.title || domain)}</span>
        `;
        sourcesList.appendChild(a);
      });
      section.appendChild(sourcesList);
    }

    const actions = wrapper.querySelector('.gemini-actions');
    if (actions) {
      wrapper.insertBefore(section, actions);
    } else {
      wrapper.appendChild(section);
    }
  }

  function attachActionButtons(row, fullText, originalPrompt = null) {
    const wrapper = row.querySelector('.message-content-wrapper');
    const existingActions = wrapper.querySelector('.gemini-actions');
    if (existingActions) existingActions.remove();

    const actions = document.createElement('div');
    actions.className = 'gemini-actions';

    // Copy Button
    const copyBtn = document.createElement('button');
    copyBtn.className = 'action-chip-btn';
    copyBtn.innerHTML = `
      <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
        <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
      </svg>
      <span>복사</span>
    `;
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(fullText).then(() => {
        const span = copyBtn.querySelector('span');
        span.textContent = '복사됨!';
        setTimeout(() => span.textContent = '복사', 2000);
      });
    });
    actions.appendChild(copyBtn);

    // Read Aloud (TTS) Button
    if ('speechSynthesis' in window) {
      const ttsBtn = document.createElement('button');
      ttsBtn.className = 'action-chip-btn';
      ttsBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
          <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
        </svg>
        <span>듣기</span>
      `;
      ttsBtn.addEventListener('click', () => {
        if (window.speechSynthesis.speaking) {
          window.speechSynthesis.cancel();
          ttsBtn.querySelector('span').textContent = '듣기';
        } else {
          const utterance = new SpeechSynthesisUtterance(fullText.replace(/[*#`_]/g, ''));
          utterance.lang = 'ko-KR';
          utterance.onend = () => ttsBtn.querySelector('span').textContent = '듣기';
          ttsBtn.querySelector('span').textContent = '중지';
          window.speechSynthesis.speak(utterance);
        }
      });
      actions.appendChild(ttsBtn);
    }

    // Regenerate Button
    if (originalPrompt) {
      const regenBtn = document.createElement('button');
      regenBtn.className = 'action-chip-btn';
      regenBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
          <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
        </svg>
        <span>다시 생성</span>
      `;
      regenBtn.addEventListener('click', () => {
        if (!isGenerating) {
          sendMessage(originalPrompt);
        }
      });
      actions.appendChild(regenBtn);
    }

    wrapper.appendChild(actions);
  }

  function scrollToBottom() {
    chatStreamContainer.scrollTop = chatStreamContainer.scrollHeight;
  }

  // =========================================================================
  // Lightweight Markdown & Code Renderer
  // =========================================================================
  function renderMarkdown(rawText) {
    if (!rawText) return '';

    // Handle code blocks ```lang\ncode```
    const codeBlocks = [];
    let text = rawText.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
      codeBlocks.push({ lang: lang || 'code', code: code.trim() });
      return placeholder;
    });

    // Escape remaining HTML to prevent XSS
    text = escapeHtml(text);

    // Headers
    text = text.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    text = text.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold and Italic
    text = text.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Inline code
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Blockquotes
    text = text.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

    // Unordered lists
    text = text.replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>)/gims, '<ul>$1</ul>');

    // Paragraphs / Line breaks
    text = text.replace(/\n{2,}/g, '</p><p>');
    text = text.replace(/\n/g, '<br>');
    text = `<p>${text}</p>`;

    // Restore Code Blocks
    codeBlocks.forEach((block, index) => {
      const escapedCode = escapeHtml(block.code);
      const codeHtml = `
        <div class="code-block-container">
          <div class="code-header">
            <span>${escapeHtml(block.lang)}</span>
            <button class="copy-code-btn" onclick="copyCode(this, '${encodeURIComponent(block.code)}')">
              <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor">
                <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
              </svg>
              <span>복사</span>
            </button>
          </div>
          <pre><code>${escapedCode}</code></pre>
        </div>
      `;
      text = text.replace(`__CODE_BLOCK_${index}__`, codeHtml);
    });

    return text;
  }

  function escapeHtml(string) {
    if (!string) return '';
    return String(string)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Global helper for code block copying
  window.copyCode = function(button, encodedCode) {
    const code = decodeURIComponent(encodedCode);
    navigator.clipboard.writeText(code).then(() => {
      const span = button.querySelector('span');
      span.textContent = '복사완료!';
      setTimeout(() => span.textContent = '복사', 2000);
    });
  };
});

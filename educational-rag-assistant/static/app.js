/**
 * LoreAI - Educational RAG Assistant
 * Client-Side Business Logic
 */

let CURRENT_USER_ID = null;
let CURRENT_CHAT_ID = null;
let CURRENT_VIEWER_STATE = null;
let CURRENT_DOCUMENT_ID = null;
let CURRENT_DOCUMENT_IDS = [];
let CURRENT_ACCESS_TOKEN = null;

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const dropZone = document.getElementById('drop-zone');
    const dragOverlay = document.getElementById('drag-overlay');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const pdfViewer = document.getElementById('pdf-viewer');
    const pdfRenderCanvas = document.getElementById('pdf-render-canvas');
    const clearContextBtn = document.getElementById('clear-context-btn');
    const sidebar = document.getElementById('sidebar');
    const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
    const sidebarCollapseBtn = document.getElementById('sidebar-collapse-btn');
    
    // Auth Modal Elements
    const authModal = document.getElementById('auth-modal');
    const headerSigninBtn = document.getElementById('header-signin-btn');
    const closeAuthBtn = document.getElementById('close-auth-btn');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const switchToRegister = document.getElementById('switch-to-register');
    const switchToLogin = document.getElementById('switch-to-login');
    const authSwitchText = document.getElementById('auth-switch-text');
    const authSwitchLogin = document.getElementById('auth-switch-login');
    
    function updateUserProfileUI(username) {
        if (username) {
            headerSigninBtn.classList.add('hidden'); // Hide "Войти" button
            const userNameEl = document.querySelector('.user-profile .user-name');
            const userAvatarEl = document.querySelector('.user-profile .avatar');
            if (userNameEl) userNameEl.textContent = username;
            if (userAvatarEl) userAvatarEl.textContent = username.charAt(0).toUpperCase();
        } else {
            headerSigninBtn.classList.remove('hidden'); // Show "Войти" button
            headerSigninBtn.textContent = "Войти";
            const userNameEl = document.querySelector('.user-profile .user-name');
            const userAvatarEl = document.querySelector('.user-profile .avatar');
            if (userNameEl) userNameEl.textContent = "Гость";
            if (userAvatarEl) userAvatarEl.textContent = "Г";
        }
    }

    // Auth Check on load
    const storedUser = localStorage.getItem("user_id");
    const storedUsername = localStorage.getItem("username");
    const storedToken = localStorage.getItem("access_token");
    if (storedUser && storedToken) {
        CURRENT_USER_ID = storedUser;
        CURRENT_ACCESS_TOKEN = storedToken;
        updateUserProfileUI(storedUsername);
    } else {
        localStorage.removeItem("user_id");
        localStorage.removeItem("username");
        localStorage.removeItem("access_token");
    }

    function authHeaders(extraHeaders = {}) {
        return {
            ...extraHeaders,
            ...(CURRENT_ACCESS_TOKEN ? { Authorization: `Bearer ${CURRENT_ACCESS_TOKEN}` } : {})
        };
    }

    // --- State Caching ---
    const CHAT_CACHE = {}; // chatId -> { html: '', title: '', viewer: null }
    
    function saveCurrentChatState() {
        if (CURRENT_CHAT_ID) {
            CHAT_CACHE[CURRENT_CHAT_ID] = {
                html: chatMessages.innerHTML,
                title: document.querySelector('.chat-title').textContent,
                viewer: CURRENT_VIEWER_STATE ? { ...CURRENT_VIEWER_STATE } : null,
                documentId: CURRENT_DOCUMENT_ID,
                documentIds: [...CURRENT_DOCUMENT_IDS]
            };
        }
    }
    
    async function loadChatState(chatId) {
        if (CHAT_CACHE[chatId]) {
            CURRENT_CHAT_ID = chatId;
            chatMessages.innerHTML = CHAT_CACHE[chatId].html;
            document.querySelector('.chat-title').textContent = CHAT_CACHE[chatId].title;
            CURRENT_DOCUMENT_ID = CHAT_CACHE[chatId].documentId || null;
            CURRENT_DOCUMENT_IDS = CHAT_CACHE[chatId].documentIds || (CURRENT_DOCUMENT_ID ? [CURRENT_DOCUMENT_ID] : []);
            restoreViewerState(CHAT_CACHE[chatId].viewer);
            scrollChatToBottom();
        } else {
            await loadChatFromServer(chatId);
        }
    }

    function scrollChatToBottom() {
        requestAnimationFrame(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }

    function activateHistoryItem(item) {
        document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
        item.classList.add('active');
    }

    async function deleteChat(chatId, item) {
        if (!CURRENT_USER_ID || !chatId) return;
        if (!confirm("Удалить этот чат?")) return;

        const resp = await fetch(`/api/chats/${chatId}?user_id=${encodeURIComponent(CURRENT_USER_ID)}`, {
            method: 'DELETE',
            headers: authHeaders()
        });
        if (!resp.ok) {
            alert("Не удалось удалить чат: " + await resp.text());
            return;
        }

        delete CHAT_CACHE[chatId];
        const wasActive = CURRENT_CHAT_ID === chatId;
        item.remove();

        if (!wasActive) return;

        const nextItem = document.querySelector('.history-item');
        if (nextItem) {
            activateHistoryItem(nextItem);
            await loadChatState(nextItem.dataset.chatId);
        } else {
            CURRENT_CHAT_ID = null;
            chatMessages.innerHTML = '';
            document.querySelector('.chat-title').textContent = "Новая сессия";
            resetViewerState();
        }
    }

    function upsertHistoryItem(chatId, title, shouldActivate = true) {
        const historyList = document.querySelector('.history-list');
        if (!historyList || !chatId) return;

        let item = historyList.querySelector(`[data-chat-id="${chatId}"]`);
        if (!item) {
            item = document.createElement('div');
            item.className = 'history-item';
            item.dataset.chatId = chatId;
            item.innerHTML = `
                <span class="history-title"></span>
                <button type="button" class="history-delete-btn" title="Удалить чат">×</button>
            `;
            item.addEventListener('click', async (event) => {
                if (event.target.closest('.history-delete-btn')) return;
                activateHistoryItem(item);
                saveCurrentChatState();
                await loadChatState(chatId);
            });
            item.querySelector('.history-delete-btn').addEventListener('click', async (event) => {
                event.stopPropagation();
                await deleteChat(chatId, item);
            });
            historyList.prepend(item);
        }

        item.querySelector('.history-title').textContent = title;
        if (shouldActivate) activateHistoryItem(item);
    }

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function renderInlineMarkdown(text) {
        return text
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    }

    function renderMarkdown(rawText) {
        const escaped = escapeHtml(rawText || '').replace(/\r\n/g, '\n');
        const codeBlocks = [];
        const withoutCode = escaped.replace(/```([\s\S]*?)```/g, (_, code) => {
            const token = `@@CODE_BLOCK_${codeBlocks.length}@@`;
            codeBlocks.push(`<pre><code>${code.trim()}</code></pre>`);
            return token;
        });

        const lines = withoutCode.split('\n');
        const html = [];
        let paragraph = [];
        let listItems = [];

        function flushParagraph() {
            if (!paragraph.length) return;
            html.push(`<p>${renderInlineMarkdown(paragraph.join(' '))}</p>`);
            paragraph = [];
        }

        function flushList() {
            if (!listItems.length) return;
            html.push(`<ul>${listItems.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul>`);
            listItems = [];
        }

        for (const line of lines) {
            const trimmed = line.trim();

            if (!trimmed) {
                flushParagraph();
                flushList();
                continue;
            }

            if (/^@@CODE_BLOCK_\d+@@$/.test(trimmed)) {
                flushParagraph();
                flushList();
                html.push(trimmed);
                continue;
            }

            const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
            if (heading) {
                flushParagraph();
                flushList();
                const level = heading[1].length + 2;
                html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
                continue;
            }

            const bullet = trimmed.match(/^[-*]\s+(.+)$/);
            if (bullet) {
                flushParagraph();
                listItems.push(bullet[1]);
                continue;
            }

            const numbered = trimmed.match(/^\d+[.)]\s+(.+)$/);
            if (numbered) {
                flushParagraph();
                listItems.push(numbered[1]);
                continue;
            }

            flushList();
            paragraph.push(trimmed);
        }

        flushParagraph();
        flushList();

        return html.join('').replace(/@@CODE_BLOCK_(\d+)@@/g, (_, index) => codeBlocks[Number(index)] || '');
    }

    function createCopyButton() {
        return '<button type="button" class="message-copy-btn" title="Скопировать сообщение">Копировать</button>';
    }

    function renderMessageContent(targetElement, rawText) {
        targetElement.dataset.rawText = rawText || '';
        targetElement.innerHTML = renderMarkdown(rawText);
    }

    function extractDocumentIdsFromMessages(messages) {
        const ids = [];
        for (const message of messages) {
            const matches = String(message.content || '').matchAll(/эмбеддинги\s+\(#([0-9a-f-]{20,})\)/gi);
            for (const match of matches) {
                if (!ids.includes(match[1])) ids.push(match[1]);
            }
        }
        return ids;
    }

    async function loadChatFromServer(chatId) {
        if (!CURRENT_USER_ID || !chatId) return;

        const resp = await fetch(`/api/chats/${chatId}/messages?user_id=${encodeURIComponent(CURRENT_USER_ID)}`, {
            headers: authHeaders()
        });
        if (!resp.ok) {
            console.warn('Failed to load chat messages:', await resp.text());
            return;
        }

        const messages = await resp.json();
        CURRENT_CHAT_ID = chatId;
        chatMessages.innerHTML = '';
        const historyItem = document.querySelector(`.history-item[data-chat-id="${chatId}"]`);
        const historyTitle = historyItem ? historyItem.querySelector('.history-title') : null;
        if (historyTitle) document.querySelector('.chat-title').textContent = historyTitle.textContent;

        if (!messages.length) {
            addMessage("Новая сессия создана. Загрузите документ или задайте обычный вопрос.", 'ai');
        } else {
            messages.forEach(message => addMessage(message.content, message.role === 'user' ? 'user' : 'ai'));
        }

        CURRENT_DOCUMENT_IDS = extractDocumentIdsFromMessages(messages);
        CURRENT_DOCUMENT_ID = CURRENT_DOCUMENT_IDS[CURRENT_DOCUMENT_IDS.length - 1] || null;
        CURRENT_VIEWER_STATE = null;
        resetViewerState();
        CURRENT_DOCUMENT_IDS = extractDocumentIdsFromMessages(messages);
        CURRENT_DOCUMENT_ID = CURRENT_DOCUMENT_IDS[CURRENT_DOCUMENT_IDS.length - 1] || null;
        saveCurrentChatState();
        scrollChatToBottom();
    }

    async function loadUserChats() {
        if (!CURRENT_USER_ID) return;

        const historyList = document.querySelector('.history-list');
        if (historyList) historyList.innerHTML = '';

        try {
            const resp = await fetch(`/api/chats?user_id=${encodeURIComponent(CURRENT_USER_ID)}`, {
                headers: authHeaders()
            });
            if (!resp.ok) throw new Error(await resp.text());

            const chats = await resp.json();
            chats.forEach(chat => upsertHistoryItem(chat.id, chat.title, false));

            if (chats.length) {
                const firstChat = chats[0];
                upsertHistoryItem(firstChat.id, firstChat.title, true);
                document.querySelector('.chat-title').textContent = firstChat.title;
                await loadChatFromServer(firstChat.id);
            }
        } catch (error) {
            console.warn('Failed to load chat history:', error);
        }
    }

    function resetViewerState() {
        CURRENT_VIEWER_STATE = null;
        CURRENT_DOCUMENT_ID = null;
        CURRENT_DOCUMENT_IDS = [];
        pdfViewer.classList.add('hidden');
        dropZone.classList.remove('hidden');
        dropZone.classList.add('empty');
        if (pdfRenderCanvas) {
            pdfRenderCanvas.classList.remove('image-preview');
            pdfRenderCanvas.classList.remove('pdf-preview');
            pdfRenderCanvas.innerHTML = `
                <div class="pdf-skeleton title"></div>
                <div class="pdf-skeleton text"></div>
                <div class="pdf-skeleton text"></div>
                <div class="pdf-skeleton text short"></div>
            `;
        }
    }

    function showLoadingViewer(file) {
        CURRENT_VIEWER_STATE = {
            type: file.type.startsWith('image/') ? 'image' : 'pdf',
            name: file.name,
            objectUrl: null,
        };
        pdfViewer.classList.remove('hidden');
        dropZone.classList.remove('empty');
    }

    function setViewerForUploadedFile(file, uploadData) {
        if (CURRENT_VIEWER_STATE && CURRENT_VIEWER_STATE.objectUrl) {
            URL.revokeObjectURL(CURRENT_VIEWER_STATE.objectUrl);
        }

        const isImage = file.type.startsWith('image/');
        const pageCount = Math.max(Number(uploadData.page_count || 1), 1);
        CURRENT_DOCUMENT_ID = uploadData.doc_id;
        if (!CURRENT_DOCUMENT_IDS.includes(uploadData.doc_id)) {
            CURRENT_DOCUMENT_IDS.push(uploadData.doc_id);
        }
        CURRENT_VIEWER_STATE = {
            type: isImage ? 'image' : 'pdf',
            name: file.name,
            objectUrl: URL.createObjectURL(file),
            docId: uploadData.doc_id,
            pageCount
        };
        restoreViewerState(CURRENT_VIEWER_STATE);
    }

    function restoreViewerState(viewerState) {
        CURRENT_VIEWER_STATE = viewerState ? { ...viewerState } : null;
        if (!CURRENT_VIEWER_STATE) {
            resetViewerState();
            return;
        }

        pdfViewer.classList.remove('hidden');
        dropZone.classList.remove('empty');
        CURRENT_DOCUMENT_ID = CURRENT_VIEWER_STATE.docId || null;
        if (CURRENT_DOCUMENT_ID && !CURRENT_DOCUMENT_IDS.includes(CURRENT_DOCUMENT_ID)) {
            CURRENT_DOCUMENT_IDS.push(CURRENT_DOCUMENT_ID);
        }

        if (!pdfRenderCanvas) return;
        if (CURRENT_VIEWER_STATE.type === 'image' && CURRENT_VIEWER_STATE.objectUrl) {
            pdfRenderCanvas.classList.add('image-preview');
            pdfRenderCanvas.classList.remove('pdf-preview');
            pdfRenderCanvas.innerHTML = `<img src="${CURRENT_VIEWER_STATE.objectUrl}" alt="${CURRENT_VIEWER_STATE.name}">`;
        } else {
            pdfRenderCanvas.classList.add('pdf-preview');
            pdfRenderCanvas.classList.remove('image-preview');
            if (CURRENT_VIEWER_STATE.objectUrl) {
                pdfRenderCanvas.innerHTML = `<iframe src="${CURRENT_VIEWER_STATE.objectUrl}" title="${CURRENT_VIEWER_STATE.name}"></iframe>`;
            } else {
                pdfRenderCanvas.innerHTML = `
                    <div class="pdf-skeleton title"></div>
                    <div class="pdf-skeleton text"></div>
                    <div class="pdf-skeleton text"></div>
                    <div class="pdf-skeleton text short"></div>
                `;
            }
        }
    }

    // --- 1. Sidebar & Auth Management ---
    if (sidebarCollapseBtn) {
        sidebarCollapseBtn.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
        });
    }

    toggleSidebarBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });

    const sidebarProfileBtn = document.getElementById('sidebar-profile-btn');
    const userMenuPopover = document.getElementById('user-menu-popover');
    if (sidebarProfileBtn && userMenuPopover) {
        sidebarProfileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            userMenuPopover.classList.toggle('hidden');
        });
        document.addEventListener('click', () => {
            userMenuPopover.classList.add('hidden');
        });
    }
    
    // Bind New Chat Sidebar Button
    const newChatBtn = document.querySelector('.new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', async () => {
            if (!CURRENT_USER_ID) return alert("Пожалуйста, войдите.");
            await createNewChatSession();
        });
    }
    
    // Bind Logout Popover Button
    const logoutPopoverBtn = document.querySelector('.popover-item.logout');
    if (logoutPopoverBtn) {
        logoutPopoverBtn.addEventListener('click', () => {
            if (confirm("Выйти из аккаунта?")) {
                localStorage.removeItem("user_id");
                localStorage.removeItem("username");
                localStorage.removeItem("access_token");
                CURRENT_USER_ID = null;
                CURRENT_CHAT_ID = null;
                CURRENT_ACCESS_TOKEN = null;
                updateUserProfileUI(null);
                chatMessages.innerHTML = '';
                const historyList = document.querySelector('.history-list');
                if (historyList) historyList.innerHTML = '';
                resetViewerState();
            }
        });
    }

    // Auth Form Switching
    switchToRegister.addEventListener('click', (e) => {
        e.preventDefault();
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        authSwitchText.classList.add('hidden');
        authSwitchLogin.classList.remove('hidden');
        document.getElementById('modal-title').textContent = "Регистрация";
    });

    switchToLogin.addEventListener('click', (e) => {
        e.preventDefault();
        registerForm.classList.add('hidden');
        loginForm.classList.remove('hidden');
        authSwitchLogin.classList.add('hidden');
        authSwitchText.classList.remove('hidden');
        document.getElementById('modal-title').textContent = "Вход в систему";
    });

    headerSigninBtn.addEventListener('click', () => {
        if (!CURRENT_USER_ID) {
            authModal.classList.remove('hidden');
        }
    });

    closeAuthBtn.addEventListener('click', () => {
        authModal.classList.add('hidden');
    });

    authModal.addEventListener('click', (e) => {
        if (e.target === authModal) authModal.classList.add('hidden');
    });

    // Login Submission
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = loginForm.querySelector('input[type="text"]').value;
        const password = loginForm.querySelector('input[type="password"]').value;

        try {
            const resp = await fetch('/api/users/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (!resp.ok) throw new Error(await resp.text());
            const data = await resp.json();
            
            CURRENT_USER_ID = data.id;
            CURRENT_ACCESS_TOKEN = data.access_token;
            localStorage.setItem("user_id", data.id);
            localStorage.setItem("username", data.username);
            localStorage.setItem("access_token", data.access_token);
            
            authModal.classList.add('hidden');
            updateUserProfileUI(data.username);
            
            // Create a default session manually implicitly
            await createNewChatSession();

        } catch (err) {
            alert("Ошибка входа: " + err.message);
        }
    });

    // Register Submission
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = registerForm.querySelector('input[type="text"]').value;
        const password = registerForm.querySelector('input[type="password"]').value;

        try {
            const resp = await fetch('/api/users/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (!resp.ok) throw new Error(await resp.text());
            const data = await resp.json();
            
            CURRENT_USER_ID = data.id;
            CURRENT_ACCESS_TOKEN = data.access_token;
            localStorage.setItem("user_id", data.id);
            localStorage.setItem("username", data.username);
            localStorage.setItem("access_token", data.access_token);
            
            authModal.classList.add('hidden');
            headerSigninBtn.classList.remove('pulse-on-upload');
            updateUserProfileUI(data.username);

            await createNewChatSession();
        } catch (err) {
            alert("Ошибка регистрации: " + err.message);
        }
    });


    // --- 2. Chat Session Setup ---
    clearContextBtn.addEventListener('click', () => {
        if (!CURRENT_USER_ID) return alert("Пожалуйста, сначала войдите в систему.");
        chatMessages.innerHTML = '';
        addMessage("Интерфейс очищен. Какой у вас вопрос?", 'ai');
        resetViewerState();
        document.querySelector('.chat-title').textContent = "Новая сессия";
    });

    async function createNewChatSession() {
        if (!CURRENT_USER_ID) return;
        try {
            saveCurrentChatState(); // Save state before wiping DOM
            const resp = await fetch('/api/chats/new', {
                method: 'POST',
                headers: authHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({ user_id: CURRENT_USER_ID })
            });
            if (!resp.ok) {
                alert("Ошибка сервера при создании чата.");
                return;
            }
            const data = await resp.json();
            CURRENT_CHAT_ID = data.id;
            const localChatId = data.id; // copy for closure
            
            chatMessages.innerHTML = '';
            addMessage("Новая сессия создана. Загрузите документ или задайте обычный вопрос.", 'ai');
            document.querySelector('.chat-title').textContent = "Новая сессия";
            resetViewerState();
            
            // init local state
            CHAT_CACHE[localChatId] = { html: chatMessages.innerHTML, title: "Новая сессия", viewer: null, documentId: null, documentIds: [] };
            
            // Визуальный фидбэк для пользователя о том, что чат создан
            const timeStr = new Date().toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit', second:'2-digit'});
            upsertHistoryItem(localChatId, "Чат " + timeStr);
        } catch (err) {
             console.error("Chat init failed", err);
        }
    }


    // --- 3. Chat Logic (Real Execution) ---
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!CURRENT_USER_ID) {
            alert("Пожалуйста, войдите в систему для использования чата.");
            return;
        }

        if (!CURRENT_CHAT_ID) await createNewChatSession();

        const userInput = chatInput.value.trim();
        if (!userInput) return;

        chatInput.value = '';
        chatInput.style.height = 'auto';

        addMessage(userInput, 'user');
        
        const aiMessageContainer = createAiMessagePlaceholder();
        chatMessages.appendChild(aiMessageContainer);
        scrollChatToBottom();

        fetchSseResponse(userInput, aiMessageContainer.querySelector('.message-content'));
    });

    function addMessage(text, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.innerHTML = `<div class="message-content"></div>${createCopyButton()}`;
        const contentEl = messageDiv.querySelector('.message-content');
        if (type === 'ai') {
            renderMessageContent(contentEl, text);
        } else {
            contentEl.dataset.rawText = text;
            contentEl.textContent = text;
        }
        chatMessages.appendChild(messageDiv);
        scrollChatToBottom();
    }

    function createAiMessagePlaceholder() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ai';
        messageDiv.innerHTML = `<div class="message-content typing"></div>${createCopyButton()}`;
        return messageDiv;
    }

    chatMessages.addEventListener('click', async (event) => {
        const copyBtn = event.target.closest('.message-copy-btn');
        if (!copyBtn) return;

        const message = copyBtn.closest('.message');
        const content = message ? message.querySelector('.message-content') : null;
        const textToCopy = content?.dataset.rawText || content?.innerText || '';
        if (!textToCopy.trim()) return;

        try {
            await navigator.clipboard.writeText(textToCopy);
            const previousText = copyBtn.textContent;
            copyBtn.textContent = 'Скопировано';
            setTimeout(() => {
                copyBtn.textContent = previousText;
            }, 1200);
        } catch (error) {
            console.warn('Copy failed:', error);
        }
    });

    async function fetchSseResponse(query, targetElement) {
        // Prepare to stream from FastAPI backend
        targetElement.classList.remove('typing');
        targetElement.innerHTML = '';
        let rawResponse = '';

        const level = document.getElementById('learner-level') ? document.getElementById('learner-level').value : 'beginner';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: authHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({
                    message: query,
                    level: level,
                    chat_id: CURRENT_CHAT_ID,
                    user_id: CURRENT_USER_ID,
                    document_id: CURRENT_DOCUMENT_ID,
                    document_ids: CURRENT_DOCUMENT_IDS
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let streamBuffer = '';
            let doneReceived = false;

            while (!doneReceived) {
                const { done, value } = await reader.read();
                if (done) {
                    streamBuffer += decoder.decode();
                    doneReceived = true;
                } else {
                    streamBuffer += decoder.decode(value, { stream: true });
                }

                const events = streamBuffer.split('\n\n');
                streamBuffer = events.pop() || '';

                for (const eventText of events) {
                    const dataLines = eventText
                        .split('\n')
                        .filter(line => line.startsWith('data: '))
                        .map(line => line.substring(6));
                    if (!dataLines.length) continue;

                    const dataStr = dataLines.join('\n').trim();
                    if (dataStr === '[DONE]') {
                        doneReceived = true;
                        break;
                    }

                    if (!dataStr) continue;

                    try {
                        const parsed = JSON.parse(dataStr);
                        
                        if (parsed.chunk) {
                            rawResponse += parsed.chunk;
                            renderMessageContent(targetElement, rawResponse);
                        }
                        
                        if (parsed.citation) {
                            rawResponse += `\n\nИсточник: ${parsed.citation}`;
                            renderMessageContent(targetElement, rawResponse);
                        }
                    } catch (e) {
                         console.warn("Parse stream err:", e, dataStr);
                    }
                    
                    scrollChatToBottom();
                }
            }
        } catch (error) {
            targetElement.textContent = "Error communicating with the agent: " + error.message;
        }
    }


    // --- 4. Drag-and-Drop File Upload (Real fetch config) ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        window.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });

    window.addEventListener('dragenter', (e) => {
        if (e.dataTransfer.types.includes('Files')) dragOverlay.classList.remove('hidden');
    });

    dragOverlay.addEventListener('dragleave', (e) => {
        if (e.relatedTarget === null || e.relatedTarget === window) dragOverlay.classList.add('hidden');
    });

    dragOverlay.addEventListener('dragover', (e) => e.preventDefault());

    dragOverlay.addEventListener('drop', (e) => {
        e.preventDefault();
        dragOverlay.classList.add('hidden');
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFilesUpload(files);
    });

    async function handleFilesUpload(files) {
        for (const file of Array.from(files)) {
            await handleFileUpload(file);
        }
    }

    async function handleFileUpload(file) {
        if (!CURRENT_USER_ID) return alert("Пожалуйста, войдите в систему перед загрузкой.");
        if (!CURRENT_CHAT_ID) await createNewChatSession();
        if (!CURRENT_CHAT_ID) return alert("Не удалось создать чат для загрузки файла.");

        const validTypes = ['application/pdf', 'image/png', 'image/jpeg'];
        if (!validTypes.includes(file.type)) return alert("Please upload a PDF or Image (PNG/JPG).");

        saveCurrentChatState();
        showLoadingViewer(file);
        document.querySelector('.chat-title').textContent = "Загрузка: " + file.name + "...";

        // Native API post
        const formData = new FormData();
        formData.append('file', file);
        formData.append('user_id', CURRENT_USER_ID);
        formData.append('chat_id', CURRENT_CHAT_ID);

        try {
            const resp = await fetch('/api/upload', {
                method: 'POST',
                headers: authHeaders(),
                body: formData
            });

            if (!resp.ok) throw new Error(await resp.text());
            const data = await resp.json();

            document.querySelector('.chat-title').textContent = file.name;
            setViewerForUploadedFile(file, data);
            const loadedCount = CURRENT_DOCUMENT_IDS.length;
            addMessage(`Я проанализировал документ **${file.name}** и сохранил его эмбеддинги (#${data.doc_id}). В текущей сессии доступно файлов: **${loadedCount}**.`, 'ai');
            saveCurrentChatState();
            upsertHistoryItem(CURRENT_CHAT_ID, file.name);
        } catch (error) {
             document.querySelector('.chat-title').textContent = "Upload Failed";
             alert("File upload failed: " + error.message);
        } finally {
            const fileUploadInput = document.getElementById('file-upload-input');
            if (fileUploadInput) fileUploadInput.value = '';
        }
    }

    // --- 5. Additional UI Bindings ---
    // File input browse logic
    const browseBtn = document.querySelector('.browse-btn');
    const attachFileBtn = document.getElementById('attach-file-btn');
    const fileUploadInput = document.getElementById('file-upload-input');
    if (browseBtn && fileUploadInput) {
        browseBtn.addEventListener('click', () => {
            fileUploadInput.click();
        });
    }

    if (attachFileBtn && fileUploadInput) {
        attachFileBtn.addEventListener('click', () => {
            fileUploadInput.click();
        });
    }

    if (fileUploadInput) {
        fileUploadInput.addEventListener('change', (e) => {
            const files = e.target.files;
            if (files.length > 0) handleFilesUpload(files);
        });
    }

    // Toggle split screen logic
    const toggleSplitBtn = document.getElementById('toggle-split-btn');
    const contentSplit = document.querySelector('.content-split');
    if (toggleSplitBtn && contentSplit) {
        toggleSplitBtn.addEventListener('click', () => {
            contentSplit.classList.toggle('viewer-collapsed');
        });
    }

    if (CURRENT_USER_ID) {
        loadUserChats();
    }
});

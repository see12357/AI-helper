/**
 * LoreAI - Educational RAG Assistant
 * Client-Side Business Logic
 */

let CURRENT_USER_ID = null;
let CURRENT_CHAT_ID = null;

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const dropZone = document.getElementById('drop-zone');
    const dragOverlay = document.getElementById('drag-overlay');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const pdfViewer = document.getElementById('pdf-viewer');
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
    if (storedUser) {
        CURRENT_USER_ID = storedUser;
        updateUserProfileUI(storedUsername);
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
                CURRENT_USER_ID = null;
                CURRENT_CHAT_ID = null;
                updateUserProfileUI(null);
                chatMessages.innerHTML = '';
            }
        });
    }

    // Auth Form Switching
    switchToRegister.addEventListener('click', (e) => {
        e.preventDefault();
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        document.getElementById('modal-title').textContent = "Регистрация";
    });

    switchToLogin.addEventListener('click', (e) => {
        e.preventDefault();
        registerForm.classList.add('hidden');
        loginForm.classList.remove('hidden');
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
            localStorage.setItem("user_id", data.id);
            localStorage.setItem("username", data.username);
            
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
            localStorage.setItem("user_id", data.id);
            localStorage.setItem("username", data.username);
            
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
        document.getElementById('pdf-viewer').classList.add('hidden');
        document.getElementById('drop-zone').classList.remove('hidden');
        document.querySelector('.chat-title').textContent = "Новая сессия";
    });

    async function createNewChatSession() {
        if (!CURRENT_USER_ID) return;
        try {
            const resp = await fetch('/api/chats/new', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: CURRENT_USER_ID })
            });
            if (!resp.ok) {
                alert("Ошибка сервера при создании чата.");
                return;
            }
            const data = await resp.json();
            CURRENT_CHAT_ID = data.id;
            chatMessages.innerHTML = '';
            addMessage("Контекст установлен. Какой у вас первый вопрос?", 'ai');
            document.querySelector('.chat-title').textContent = "Новая сессия";
            document.getElementById('pdf-viewer').classList.add('hidden');
            document.getElementById('drop-zone').classList.remove('hidden');
            
            // Визуальный фидбэк для пользователя о том, что чат создан
            const historyList = document.querySelector('.history-list');
            if (historyList) {
                document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
                const item = document.createElement('div');
                item.className = 'history-item active';
                // Генерируем название с текущим временем чтобы было видно разницу
                const timeStr = new Date().toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit', second:'2-digit'});
                item.textContent = "Чат " + timeStr;
                item.addEventListener('click', () => {
                    document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
                    item.classList.add('active');
                });
                historyList.prepend(item);
            }
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
        chatMessages.scrollTop = chatMessages.scrollHeight;

        fetchSseResponse(userInput, aiMessageContainer.querySelector('.message-content'));
    });

    function addMessage(text, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.innerHTML = `<div class="message-content">${text}</div>`;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function createAiMessagePlaceholder() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ai';
        messageDiv.innerHTML = `<div class="message-content typing"></div>`;
        return messageDiv;
    }

    async function fetchSseResponse(query, targetElement) {
        // Prepare to stream from FastAPI backend
        targetElement.classList.remove('typing');
        targetElement.innerHTML = ''; 

        const level = document.getElementById('learner-level') ? document.getElementById('learner-level').value : 'beginner';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: query,
                    level: level,
                    chat_id: CURRENT_CHAT_ID,
                    user_id: CURRENT_USER_ID
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunkStr = decoder.decode(value, { stream: true });
                const lines = chunkStr.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.substring(6).trim();
                        if (dataStr === '[DONE]') {
                            break; 
                        }

                        if (!dataStr) continue;

                        try {
                            const parsed = JSON.parse(dataStr);
                            
                            if (parsed.chunk) {
                                targetElement.innerHTML += parsed.chunk;
                            }
                            
                            if (parsed.citation) {
                                const citationSpan = `<br><span class="citation-badge" title="Перейти к источнику">${parsed.citation}</span>`;
                                targetElement.innerHTML += citationSpan;
                            }
                        } catch (e) {
                             console.warn("Parse stream err:", e, dataStr);
                        }
                        
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
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
        if (files.length > 0) handleFileUpload(files[0]);
    });

    async function handleFileUpload(file) {
        if (!CURRENT_USER_ID) return alert("Пожалуйста, войдите в систему перед загрузкой.");

        const validTypes = ['application/pdf', 'image/png', 'image/jpeg'];
        if (!validTypes.includes(file.type)) return alert("Please upload a PDF or Image (PNG/JPG).");

        document.getElementById('drop-zone').classList.remove('empty');
        pdfViewer.classList.remove('hidden');
        document.querySelector('.chat-title').textContent = "Загрузка: " + file.name + "...";

        // Native API post
        const formData = new FormData();
        formData.append('file', file);
        formData.append('user_id', CURRENT_USER_ID);

        try {
            const resp = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!resp.ok) throw new Error(await resp.text());
            const data = await resp.json();

            document.querySelector('.chat-title').textContent = file.name;
            addMessage(`Я проанализировал документ <strong>${file.name}</strong> и сохранил его эмбеддинги (#${data.doc_id}). Теперь я готов отвечать на вопросы по его содержанию.`, 'ai');
            
            const historyList = document.querySelector('.history-list');
            if (historyList) {
                document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
                const item = document.createElement('div');
                item.className = 'history-item active';
                item.textContent = file.name;
                item.addEventListener('click', () => {
                    document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
                    item.classList.add('active');
                    document.getElementById('pdf-viewer').classList.remove('hidden');
                    document.querySelector('.chat-title').textContent = file.name;
                });
                historyList.prepend(item);
            }
        } catch (error) {
             document.querySelector('.chat-title').textContent = "Upload Failed";
             alert("File upload failed: " + error.message);
        }
    }

    const closePdfBtn = document.getElementById('close-pdf-btn');
    if (closePdfBtn) {
        closePdfBtn.addEventListener('click', () => {
            pdfViewer.classList.add('hidden');
            document.getElementById('drop-zone').classList.add('empty');
            document.querySelector('.chat-title').textContent = "Новая сессия";
        });
    }

    // --- 5. Additional UI Bindings ---
    // File input browse logic
    const browseBtn = document.querySelector('.browse-btn');
    const fileUploadInput = document.getElementById('file-upload-input');
    if (browseBtn && fileUploadInput) {
        browseBtn.addEventListener('click', () => {
            fileUploadInput.click();
        });
        
        fileUploadInput.addEventListener('change', (e) => {
            const files = e.target.files;
            if (files.length > 0) handleFileUpload(files[0]);
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

    // PDF Zoom Logic
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const zoomLevelEl = document.querySelector('.zoom-level');
    const pdfRenderCanvas = document.getElementById('pdf-render-canvas');
    let currentZoom = 100;
    
    if (zoomInBtn && zoomOutBtn && zoomLevelEl && pdfRenderCanvas) {
        zoomInBtn.addEventListener('click', () => {
            if (currentZoom < 300) {
                currentZoom += 25;
                updateZoom();
            }
        });
        zoomOutBtn.addEventListener('click', () => {
            if (currentZoom > 50) {
                currentZoom -= 25;
                updateZoom();
            }
        });
        
        function updateZoom() {
            zoomLevelEl.textContent = `${currentZoom}%`;
            pdfRenderCanvas.style.transform = `scale(${currentZoom / 100})`;
            pdfRenderCanvas.style.transformOrigin = 'top center';
        }
    }
});

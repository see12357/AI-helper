import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "educational-rag-assistant" / "static"


def read_static_file(filename: str) -> str:
    return (STATIC_DIR / filename).read_text(encoding="utf-8")


class UiUxRequirementsTest(unittest.TestCase):
    """UI/UX checks for the designer test cases."""

    @classmethod
    def setUpClass(cls):
        cls.html = read_static_file("index.html")
        cls.css = read_static_file("styles.css")
        cls.js = read_static_file("app.js")

    def test_mobile_layout_has_adaptive_breakpoints(self):
        self.assertIn('@media (max-width: 1024px)', self.css)
        self.assertIn('@media (max-width: 768px)', self.css)
        self.assertRegex(self.css, r"\.content-split\s*\{[^}]*grid-template-rows:\s*1fr 1fr;")
        self.assertRegex(self.css, r"\.content-split\s*\{[^}]*display:\s*block;")
        self.assertIn("toggle-sidebar-btn", self.html)
        self.assertIn(".sidebar.open", self.css)

    def test_split_screen_toggle_is_available_and_collapses_viewer(self):
        self.assertIn('id="toggle-split-btn"', self.html)
        self.assertIn("Разделить", self.html)
        self.assertIn("contentSplit.classList.toggle('viewer-collapsed')", self.js)
        self.assertRegex(
            self.css,
            r"\.content-split\.viewer-collapsed\s*\{[^}]*grid-template-columns:\s*1fr 0px;",
        )

    def test_file_upload_supports_button_and_drag_drop(self):
        self.assertIn('id="drop-zone"', self.html)
        self.assertIn('id="file-upload-input"', self.html)
        self.assertIn('accept=".pdf,image/png,image/jpeg"', self.html)
        self.assertIn("multiple", self.html)
        self.assertIn('id="attach-file-btn"', self.html)
        self.assertIn("fileUploadInput.click()", self.js)
        self.assertIn("dragOverlay.addEventListener('drop'", self.js)
        self.assertIn("handleFilesUpload(files)", self.js)
        self.assertIn("for (const file of Array.from(files))", self.js)

    def test_file_upload_validates_formats_and_requires_login(self):
        self.assertIn('if (!CURRENT_USER_ID) return alert("Пожалуйста, войдите в систему перед загрузкой.")', self.js)
        self.assertIn("const validTypes = ['application/pdf', 'image/png', 'image/jpeg'];", self.js)
        self.assertIn("validTypes.includes(file.type)", self.js)
        self.assertIn("Please upload a PDF or Image (PNG/JPG).", self.js)

    def test_upload_flow_gives_clear_visual_feedback(self):
        self.assertIn('class="drag-overlay hidden"', self.html)
        self.assertIn("Загрузка: ", self.js)
        self.assertIn("Я проанализировал документ", self.js)
        self.assertIn("upsertHistoryItem(CURRENT_CHAT_ID, file.name)", self.js)
        self.assertIn('historyList.querySelector(`[data-chat-id="${chatId}"]`)', self.js)
        self.assertIn("if (!CURRENT_CHAT_ID) await createNewChatSession()", self.js)
        self.assertIn("fileUploadInput.value = ''", self.js)
        self.assertIn("pdfViewer.classList.remove('hidden')", self.js)

    def test_empty_chat_does_not_claim_document_context(self):
        self.assertNotIn("Контекст установлен. Какой у вас первый вопрос?", self.js)
        self.assertIn("Новая сессия создана. Загрузите документ или задайте обычный вопрос.", self.js)

    def test_chat_messages_render_markdown_and_can_be_copied(self):
        self.assertIn("function renderMarkdown(rawText)", self.js)
        self.assertIn("function renderMessageContent(targetElement, rawText)", self.js)
        self.assertIn("navigator.clipboard.writeText", self.js)
        self.assertIn("message-copy-btn", self.js)
        self.assertIn(".message-copy-btn", self.css)
        self.assertIn("<strong>$1</strong>", self.js)
        self.assertIn("<ul>", self.js)

    def test_chat_history_loads_after_page_refresh(self):
        self.assertIn("async function loadUserChats()", self.js)
        self.assertIn("async function loadChatFromServer(chatId)", self.js)
        self.assertIn("fetch(`/api/chats?user_id=", self.js)
        self.assertIn("fetch(`/api/chats/${chatId}/messages?user_id=", self.js)
        self.assertIn("if (CURRENT_USER_ID) {\n        loadUserChats();", self.js)
        self.assertIn("formData.append('chat_id', CURRENT_CHAT_ID)", self.js)

    def test_frontend_sends_auth_token_for_user_scoped_requests(self):
        self.assertIn("CURRENT_ACCESS_TOKEN", self.js)
        self.assertIn("localStorage.setItem(\"access_token\", data.access_token)", self.js)
        self.assertIn("Authorization: `Bearer ${CURRENT_ACCESS_TOKEN}`", self.js)
        self.assertIn("headers: authHeaders({ 'Content-Type': 'application/json' })", self.js)
        self.assertIn("headers: authHeaders()", self.js)

    def test_chat_history_items_can_be_deleted(self):
        self.assertIn("async function deleteChat(chatId, item)", self.js)
        self.assertIn("method: 'DELETE'", self.js)
        self.assertIn("history-delete-btn", self.js)
        self.assertIn(".history-delete-btn", self.css)
        self.assertIn("delete CHAT_CACHE[chatId]", self.js)

    def test_viewer_state_resets_between_documents(self):
        self.assertNotIn("Страница 1 / 24", self.html)
        self.assertIn("CURRENT_VIEWER_STATE", self.js)
        self.assertIn("CURRENT_DOCUMENT_ID", self.js)
        self.assertIn("CURRENT_DOCUMENT_IDS", self.js)
        self.assertIn("resetViewerState()", self.js)
        self.assertIn("setViewerForUploadedFile(file, data)", self.js)
        self.assertIn("document_id: CURRENT_DOCUMENT_ID", self.js)
        self.assertIn("document_ids: CURRENT_DOCUMENT_IDS", self.js)
        self.assertIn("page_count", self.js)
        self.assertIn("pdf-preview", self.css)
        self.assertIn("<iframe", self.js)
        self.assertNotIn("zoom-in", self.html)
        self.assertNotIn("zoom-out", self.html)
        self.assertNotIn("zoom-level", self.html)
        self.assertNotIn("pdfRenderCanvas.style.transform", self.js)
        self.assertIn("viewer: CURRENT_VIEWER_STATE", self.js)


if __name__ == "__main__":
    unittest.main()

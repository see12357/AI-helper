import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "educational-rag-assistant"
sys.path.insert(0, str(APP_ROOT))

from app.services.processor import DocumentProcessor
from app.services.vector_store_service import VectorStoreService


def test_document_processor_rejects_unsupported_mime_type():
    processor = DocumentProcessor()

    with pytest.raises(ValueError, match="Unsupported mime-type"):
        import asyncio

        asyncio.run(processor.process_file(b"plain text", "text/plain"))


def test_document_processor_extracts_text_from_pdf_fixture():
    processor = DocumentProcessor()
    pdf_bytes = (PROJECT_ROOT / "tests" / "fixtures" / "sample_upload.pdf").read_bytes()

    extracted_text = processor._process_pdf_sync(pdf_bytes)

    assert "--- Page 1 ---" in extracted_text
    assert "Simulated GLM OCR Extracted Text" in extracted_text


def test_document_processor_uses_tesseract_for_images(monkeypatch):
    processor = DocumentProcessor()

    def fake_run(*args, **kwargs):
        return SimpleNamespace(stdout="Распознанный текст".encode("utf-8"), stderr=b"")

    monkeypatch.setattr("app.services.processor.subprocess.run", fake_run)

    extracted_text = processor._process_image_sync(b"image-bytes")

    assert extracted_text == "Распознанный текст"


def test_vector_store_rejects_payload_count_mismatch():
    vector_store = VectorStoreService()

    with pytest.raises(Exception, match="Vectors and payloads must have the same length"):
        vector_store.upsert_vectors(vectors=[[0.1, 0.2]], payloads=[])


def test_vector_store_generates_ids_for_valid_vectors():
    vector_store = VectorStoreService()

    ids = vector_store.upsert_vectors(
        vectors=[[0.1, 0.2], [0.3, 0.4]],
        payloads=[{"document_id": "doc-1"}, {"document_id": "doc-2"}],
    )

    assert len(ids) == 2
    assert all(isinstance(item, str) and item for item in ids)


def test_chat_endpoint_does_not_search_old_documents_without_document_id():
    main_py = (APP_ROOT / "app" / "main.py").read_text(encoding="utf-8")

    assert "if scoped_document_ids:" in main_py
    assert "document_ids=scoped_document_ids" in main_py
    assert "Нельзя ссылаться на старые документы пользователя" in main_py
    assert "yield f\"data: {json.dumps({'citation':" in main_py


def test_backend_exposes_chat_history_endpoints():
    main_py = (APP_ROOT / "app" / "main.py").read_text(encoding="utf-8")

    assert '@app.get("/api/chats"' in main_py
    assert '@app.get("/api/chats/{chat_id}/messages"' in main_py
    assert '@app.delete("/api/chats/{chat_id}")' in main_py
    assert "chat.title = file.filename" in main_py


def test_backend_uses_signed_tokens_and_password_hashing():
    main_py = (APP_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    schemas_py = (APP_ROOT / "app" / "schemas.py").read_text(encoding="utf-8")

    assert "hashlib.pbkdf2_hmac" in main_py
    assert "create_access_token" in main_py
    assert "get_current_user_id" in main_py
    assert "ensure_same_user" in main_py
    assert "access_token: str" in schemas_py


def test_embedder_keeps_source_metadata_for_citations():
    embedder_py = (APP_ROOT / "app" / "services" / "embedder.py").read_text(encoding="utf-8")

    assert "_chunk_text_with_pages_sync" in embedder_py
    assert "page_number" in embedder_py
    assert "filename" in embedder_py
    assert "MatchAny" in embedder_py

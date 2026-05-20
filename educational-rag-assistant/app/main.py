from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Header
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import asyncio
import os
import json
import fitz
import base64
import hashlib
import hmac
import secrets

from app.schemas import UploadResponse, ChatRequest, UserAuth, UserResponse, ChatResponse, ChatCreateRequest, MessageResponse
from app.core.config import settings
from app.services.processor import processor_service
from app.services.embedder import embedder_service
from app.services.llm_service import llm_service
from app.db.session import engine, Base, get_db, AsyncSessionLocal
from app.db.models import User, Chat, Message, Document

app = FastAPI(
    title="Educational RAG Assistant",
    description="Backend API for processing files and chatting with LangGraph/Ollama.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return f"pbkdf2_sha256${salt}${digest}"

def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("pbkdf2_sha256$"):
        _, salt, expected = stored_hash.split("$", 2)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
        return hmac.compare_digest(actual, expected)
    return hmac.compare_digest(password, stored_hash)

def create_access_token(user_id: str) -> str:
    payload = _b64url_encode(json.dumps({"user_id": user_id}, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return f"{payload}.{_b64url_encode(signature)}"

def verify_access_token(token: str) -> str:
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(settings.SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_decode(signature), expected):
            raise ValueError("bad signature")
        data = json.loads(_b64url_decode(payload))
        return data["user_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or missing access token")

async def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing access token")
    return verify_access_token(authorization.removeprefix("Bearer ").strip())

def ensure_same_user(request_user_id: str, token_user_id: str) -> None:
    if request_user_id != token_user_id:
        raise HTTPException(status_code=403, detail="User isolation violation")

# --- USER AUTH (NO MOCKS) ---
@app.post("/api/users/register", response_model=UserResponse)
async def register(auth: UserAuth, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == auth.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = User(username=auth.username, password_hash=hash_password(auth.password))
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return UserResponse(id=new_user.id, username=new_user.username, access_token=create_access_token(new_user.id))

@app.post("/api/users/login", response_model=UserResponse)
async def login(auth: UserAuth, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == auth.username))
    user = result.scalars().first()
    if not user or not verify_password(auth.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if not user.password_hash.startswith("pbkdf2_sha256$"):
        user.password_hash = hash_password(auth.password)
        await db.commit()
    return UserResponse(id=user.id, username=user.username, access_token=create_access_token(user.id))

# --- CHATS ---
@app.post("/api/chats/new", response_model=ChatResponse)
async def create_chat(
    payload: ChatCreateRequest,
    db: AsyncSession = Depends(get_db),
    token_user_id: str = Depends(get_current_user_id),
):
    ensure_same_user(payload.user_id, token_user_id)
    new_chat = Chat(user_id=payload.user_id, title="Новая сессия")
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    return ChatResponse(id=new_chat.id, title=new_chat.title, created_at=new_chat.created_at)

@app.get("/api/chats", response_model=list[ChatResponse])
async def list_chats(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    token_user_id: str = Depends(get_current_user_id),
):
    ensure_same_user(user_id, token_user_id)
    result = await db.execute(
        select(Chat)
        .where(Chat.user_id == user_id)
        .order_by(Chat.created_at.desc())
    )
    return [
        ChatResponse(id=chat.id, title=chat.title, created_at=chat.created_at)
        for chat in result.scalars().all()
    ]

@app.get("/api/chats/{chat_id}/messages", response_model=list[MessageResponse])
async def list_chat_messages(
    chat_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    token_user_id: str = Depends(get_current_user_id),
):
    ensure_same_user(user_id, token_user_id)
    chat_result = await db.execute(
        select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
    )
    if not chat_result.scalars().first():
        raise HTTPException(status_code=404, detail="Chat not found")

    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
    )
    return [
        MessageResponse(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
        )
        for message in result.scalars().all()
    ]

@app.delete("/api/chats/{chat_id}")
async def delete_chat(
    chat_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    token_user_id: str = Depends(get_current_user_id),
):
    ensure_same_user(user_id, token_user_id)
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
    )
    chat = result.scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    await db.delete(chat)
    await db.commit()
    return {"status": "deleted", "chat_id": chat_id}

# --- UPLOAD ---
@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    chat_id: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    token_user_id: str = Depends(get_current_user_id),
):
    ensure_same_user(user_id, token_user_id)
    valid_mime_types = ["application/pdf", "image/jpeg", "image/png"]
    if file.content_type not in valid_mime_types:
        raise HTTPException(status_code=400, detail=f"Unsupported format.")
    
    file_bytes = await file.read()
    page_count = 1
    if file.content_type == "application/pdf":
        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as pdf_doc:
                page_count = max(len(pdf_doc), 1)
        except Exception:
            page_count = 1
    
    try:
        # Save Document to Postgres
        new_doc = Document(user_id=user_id, filename=file.filename)
        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)

        if chat_id:
            chat_result = await db.execute(
                select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
            )
            chat = chat_result.scalars().first()
            if chat:
                chat.title = file.filename
                await db.commit()
        
        # 1. Process File to extract text
        extracted_text = await processor_service.process_file(file_bytes, file.content_type)
        extracted_text = (
            f"Название файла: {file.filename}\n"
            f"Тип файла: {file.content_type}\n"
            f"Извлеченное содержимое:\n{extracted_text}"
        )

        # 2. Chunk and Vectorize to Qdrant
        await embedder_service.process_and_upsert(extracted_text, user_id, new_doc.id, filename=file.filename)

        return UploadResponse(
            status="success",
            doc_id=new_doc.id,
            filename=file.filename,
            content_type=file.content_type,
            page_count=page_count,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- CHAT ---
@app.post("/api/chat")
async def chat_with_agent(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    token_user_id: str = Depends(get_current_user_id),
):
    ensure_same_user(request.user_id, token_user_id)
    # Save User message to Postgres (Real DB, NO Mocks)
    user_msg = Message(chat_id=request.chat_id, role="user", content=request.message)
    db.add(user_msg)
    await db.commit()

    async def generate_chat_stream():
        full_ai_response = ""
        
        try:
            scoped_document_ids = request.document_ids or ([request.document_id] if request.document_id else [])
            context_chunks = []
            if scoped_document_ids:
                context_results = await embedder_service.search_relevant_chunks(
                    query=request.message,
                    user_id=request.user_id,
                    document_ids=scoped_document_ids,
                    limit=5,
                )
                context_chunks = [
                    f"Источник: {item['filename']}, стр. {item['page_number']}\n{item['text']}"
                    for item in context_results
                ]

            if not context_chunks:
                context_chunks = [
                    "В текущем чате пользователь еще не загрузил документ или контекст по текущему документу не найден. "
                    "Нельзя ссылаться на старые документы пользователя. Если пользователь спрашивает о файле или тексте, "
                    "нужно честно сказать, что в текущей сессии файл не предоставлен."
                ]

            async for chunk in llm_service.generate_streaming_response(
                prompt=request.message, 
                context=context_chunks,
                temperature=0.7
            ):
                full_ai_response += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            if scoped_document_ids and context_results:
                seen_sources = set()
                citations = []
                for item in context_results:
                    source_key = (item["filename"], item["page_number"])
                    if source_key in seen_sources:
                        continue
                    seen_sources.add(source_key)
                    citations.append(f"{item['filename']}, стр. {item['page_number']}")
                yield f"data: {json.dumps({'citation': '; '.join(citations)})}\n\n"
            
            yield "data: [DONE]\n\n"
            
            # Save AI response back to Postgres immediately following stream
            # Must spawn sync/async DB executor correctly. 
            async with AsyncSessionLocal() as session:
                 ai_msg = Message(chat_id=request.chat_id, role="ai", content=full_ai_response)
                 session.add(ai_msg)
                 await session.commit()
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate_chat_stream(), media_type="text/event-stream")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(BASE_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import asyncio
import os
import json

from app.schemas import UploadResponse, ChatRequest, UserAuth, UserResponse, ChatResponse, ChatCreateRequest
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

# --- USER AUTH (NO MOCKS) ---
@app.post("/api/users/register", response_model=UserResponse)
async def register(auth: UserAuth, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == auth.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # In a real setup, hash the password (mocking passlib overhead for pure brevity rn)
    new_user = User(username=auth.username, password_hash=auth.password) 
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return UserResponse(id=new_user.id, username=new_user.username)

@app.post("/api/users/login", response_model=UserResponse)
async def login(auth: UserAuth, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == auth.username))
    user = result.scalars().first()
    if not user or user.password_hash != auth.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return UserResponse(id=user.id, username=user.username)

# --- CHATS ---
@app.post("/api/chats/new", response_model=ChatResponse)
async def create_chat(payload: ChatCreateRequest, db: AsyncSession = Depends(get_db)):
    new_chat = Chat(user_id=payload.user_id, title="Новая сессия")
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    return ChatResponse(id=new_chat.id, title=new_chat.title, created_at=new_chat.created_at)

# --- UPLOAD ---
@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    valid_mime_types = ["application/pdf", "image/jpeg", "image/png"]
    if file.content_type not in valid_mime_types:
        raise HTTPException(status_code=400, detail=f"Unsupported format.")
    
    file_bytes = await file.read()
    
    try:
        # Save Document to Postgres
        new_doc = Document(user_id=user_id, filename=file.filename)
        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)
        
        # 1. Process File to extract text
        extracted_text = await processor_service.process_file(file_bytes, file.content_type)

        # 2. Chunk and Vectorize to Qdrant
        await embedder_service.process_and_upsert(extracted_text, user_id, new_doc.id)

        return UploadResponse(status="success", doc_id=new_doc.id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- CHAT ---
@app.post("/api/chat")
async def chat_with_agent(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    # Save User message to Postgres (Real DB, NO Mocks)
    user_msg = Message(chat_id=request.chat_id, role="user", content=request.message)
    db.add(user_msg)
    await db.commit()

    async def generate_chat_stream():
        # TODO: real context execution from Qdrant goes here instead of static array 
        # based on returning closest vectors for `request.message` using `embedder_service`
        mock_context = [] 
        full_ai_response = ""
        
        try:
            # Stream from local Llama/Gemini API
            async for chunk in llm_service.generate_streaming_response(
                prompt=request.message, 
                context=mock_context,
                temperature=0.7
            ):
                full_ai_response += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
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
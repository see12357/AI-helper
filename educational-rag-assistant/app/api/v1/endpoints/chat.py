# API эндпоинты для чата и RAG операций
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.core.exceptions import (
    DocumentProcessingException,
    OCRException,
    EmbedderException,
    VectorStoreException
)
from app.schemas.document import (
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionInDB,
    ChatSessionWithMessages,
    ChatMessageCreate,
    ChatMessageUpdate,
    ChatMessageInDB,
    QueryRequest,
    QueryResponse
)
from app.models.document import ChatSession, ChatMessage
from app.services.ocr_service import OCRService
from app.services.embedder_service import EmbedderService
from app.services.vector_store_service import VectorStoreService
from app.core.config import settings

router = APIRouter()

@router.post("/sessions", response_model=ChatSessionInDB)
async def create_chat_session(
    session_create: ChatSessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создание новой сессии чата"""
    session_id = str(uuid.uuid4())
    
    db_session = ChatSession(
        session_id=session_id,
        **session_create.dict()
    )
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    
    return db_session

@router.get("/sessions", response_model=List[ChatSessionInDB])
async def get_chat_sessions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получение списка сессий чата"""
    from sqlalchemy import select
    result = await db.execute(
        select(ChatSession).offset(skip).limit(limit)
    )
    sessions = result.scalars().all()
    return sessions

@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessages)
async def get_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Получение сессии чата по ID с сообщениями"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .filter(ChatSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    return session

@router.put("/sessions/{session_id}", response_model=ChatSessionInDB)
async def update_chat_session(
    session_id: str,
    session_update: ChatSessionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление сессии чата"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(ChatSession).filter(ChatSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    update_data = session_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)
    
    await db.commit()
    await db.refresh(session)
    
    return session

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Удаление сессии чата"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(ChatSession).filter(ChatSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    await db.delete(session)
    await db.commit()
    
    return None

@router.post("/sessions/{session_id}/messages", response_model=ChatMessageInDB)
async def add_chat_message(
    session_id: str,
    message_create: ChatMessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """Добавление сообщения в сессию чата"""
    from sqlalchemy import select
    
    # Проверяем существование сессии
    result = await db.execute(
        select(ChatSession).filter(ChatSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    db_message = ChatMessage(
        session_id=session.id,
        **message_create.dict()
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    
    return db_message

@router.put("/sessions/{session_id}/messages/{message_id}", response_model=ChatMessageInDB)
async def update_chat_message(
    session_id: str,
    message_id: int,
    message_update: ChatMessageUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление сообщения в сессии чата"""
    from sqlalchemy import select
    
    # Проверяем существование сессии
    result = await db.execute(
        select(ChatSession).filter(ChatSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    # Проверяем существование сообщения
    result = await db.execute(
        select(ChatMessage).filter(
            ChatSession.id == session.id,
            ChatMessage.id == message_id
        )
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat message not found"
        )
    
    update_data = message_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(message, field, value)
    
    await db.commit()
    await db.refresh(message)
    
    return message

@router.delete("/sessions/{session_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_message(
    session_id: str,
    message_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удаление сообщения из сессии чата"""
    from sqlalchemy import select
    
    # Проверяем существование сессии
    result = await db.execute(
        select(ChatSession).filter(ChatSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    # Проверяем существование сообщения
    result = await db.execute(
        select(ChatMessage).filter(
            ChatSession.id == session.id,
            ChatMessage.id == message_id
        )
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat message not found"
        )
    
    await db.delete(message)
    await db.commit()
    
    return None

@router.post("/query", response_model=QueryResponse)
async def process_query(
    query_request: QueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """Обработка RAG запроса"""
    import time
    start_time = time.time()
    
    # TODO: Реализовать полную RAG логику
    # Для простоты пока возвращаем заглушку
    
    processing_time = time.time() - start_time
    
    return QueryResponse(
        answer="This is a placeholder response. RAG functionality will be implemented soon.",
        session_id=query_request.session_id or str(uuid.uuid4()),
        sources=[],
        confidence_score=0.8,
        processing_time=processing_time
    )
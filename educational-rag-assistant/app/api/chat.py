# Чат, история, стриминг (SSE)
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from app.core.database import get_db
from app.models.user import User
from app.schemas.chat_schema import ChatMessage, ChatResponse
from app.services.rag_agent import rag_agent
from app.core.security import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/message", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Process chat message with RAG
    response = await rag_agent.process_query(
        query=message.content,
        user_id=current_user.id,
        db=db
    )
    
    return ChatResponse(
        response=response["answer"],
        sources=response.get("sources", []),
        conversation_id=response.get("conversation_id")
    )

@router.post("/stream")
async def stream_message(
    message: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Stream chat response using Server-Sent Events
    async def event_generator() -> AsyncGenerator[str, None]:
        async for chunk in rag_agent.stream_query(
            query=message.content,
            user_id=current_user.id,
            db=db
        ):
            yield f"data: {chunk}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/plain"
    )
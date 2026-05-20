from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class UploadResponse(BaseModel):
    status: str
    doc_id: str
    filename: str
    content_type: str
    page_count: int

class UserAuth(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    access_token: str

class ChatCreateRequest(BaseModel):
    user_id: str

class ChatResponse(BaseModel):
    id: str
    title: str
    created_at: datetime

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

class ChatRequest(BaseModel):
    message: str = Field(..., description="User's text message input")
    level: str = Field(default="beginner", description="Educational level of the user")
    chat_id: str = Field(..., description="The ID of the current chat session")
    user_id: str = Field(..., description="The ID of the user")
    document_id: Optional[str] = Field(default=None, description="Optional current document ID for scoped RAG search")
    document_ids: Optional[List[str]] = Field(default=None, description="Optional current document IDs for scoped RAG search")

class DocumentMetadata(BaseModel):
    user_id: str
    document_id: str
    page_number: str
    chunk_text: str

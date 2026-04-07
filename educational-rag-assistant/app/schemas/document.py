# Pydantic схемы для валидации данных
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

# Пользовательские схемы
class UserBase(BaseModel):
    email: str
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

class UserInDBBase(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class UserInDB(UserInDBBase):
    hashed_password: str

class User(UserInDBBase):
    pass

# Схемы для документов
class DocumentBase(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_processed: Optional[bool] = None
    processing_status: Optional[str] = None

class DocumentInDBBase(DocumentBase):
    id: int
    uuid: str
    is_processed: bool
    processing_status: str
    error_message: Optional[str] = None
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class DocumentInDB(DocumentInDBBase):
    pass

class Document(DocumentInDBBase):
    pass

class DocumentWithChunks(Document):
    chunks: List["DocumentChunk"] = []

# Схемы для чанков документов
class DocumentChunkBase(BaseModel):
    content: str
    chunk_index: int
    token_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class DocumentChunkCreate(DocumentChunkBase):
    document_id: int
    embedding: Optional[List[float]] = None

class DocumentChunkUpdate(BaseModel):
    content: Optional[str] = None
    chunk_index: Optional[int] = None
    token_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class DocumentChunkInDBBase(DocumentChunkBase):
    id: int
    document_id: int
    embedding: Optional[List[float]] = None
    created_at: datetime

    class Config:
        orm_mode = True

class DocumentChunkInDB(DocumentChunkInDBBase):
    pass

class DocumentChunk(DocumentChunkInDBBase):
    pass

# Схемы для чата
class ChatSessionBase(BaseModel):
    title: Optional[str] = None

class ChatSessionCreate(ChatSessionBase):
    pass

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    is_active: Optional[bool] = None

class ChatSessionInDBBase(ChatSessionBase):
    id: int
    session_id: str
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool

    class Config:
        orm_mode = True

class ChatSessionInDB(ChatSessionInDBBase):
    pass

class ChatSession(ChatSessionInDBBase):
    pass

class ChatMessageBase(BaseModel):
    message_type: str  # user, assistant, system
    content: str
    metadata: Optional[Dict[str, Any]] = None

class ChatMessageCreate(ChatMessageBase):
    session_id: int

class ChatMessageUpdate(BaseModel):
    content: Optional[str] = None
    message_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatMessageInDBBase(ChatMessageBase):
    id: int
    session_id: int
    created_at: datetime

    class Config:
        orm_mode = True

class ChatMessageInDB(ChatMessageInDBBase):
    pass

class ChatMessage(ChatMessageInDBBase):
    pass

class ChatSessionWithMessages(ChatSession):
    messages: List[ChatMessage] = []

# Схемы для аутентификации
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

# Схемы для RAG операций
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    top_k: Optional[int] = None
    include_sources: bool = True

class QueryResponse(BaseModel):
    answer: str
    session_id: str
    sources: List[Dict[str, Any]] = []
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None

class DocumentUploadResponse(BaseModel):
    document_id: int
    uuid: str
    title: str
    message: str = "Document uploaded successfully"

# Обновляем forward references
DocumentWithChunks.update_forward_refs()
ChatSessionWithMessages.update_forward_refs()
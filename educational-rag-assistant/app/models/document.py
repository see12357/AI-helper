# SQLAlchemy модели для документов, чанков, пользователей и т.д.
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from typing import Optional, List
import uuid

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Отношения
    documents = relationship("Document", back_populates="owner")
    chat_sessions = relationship("ChatSession", back_populates="user")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    file_path = Column(String(1000))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)
    metadata = Column(JSON)  # Для хранения дополнительных метаданных
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Отношения
    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    # Индексы для быстрого поиска
    __table_args__ = (
        Index('idx_documents_owner', 'owner_id'),
        Index('idx_documents_processed', 'is_processed'),
        Index('idx_documents_created', 'created_at'),
    )

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Позиция чанка в документе
    content = Column(Text, nullable=False)
    embedding = Column(JSON)  # Векторное представление (в реальном проекте лучше использовать специальный тип)
    token_count = Column(Integer)
    metadata = Column(JSON)  # Метаданные чанка
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Отношения
    document = relationship("Document", back_populates="chunks")
    
    # Индексы
    __table_args__ = (
        Index('idx_chunks_document', 'document_id'),
        Index('idx_chunks_created', 'created_at'),
    )

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Отношения
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    message_type = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    metadata = Column(JSON)  # Для хранения источников, confidence score и т.д.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Отношения
    session = relationship("ChatSession", back_populates="messages")
    
    # Индексы
    __table_args__ = (
        Index('idx_messages_session', 'session_id'),
        Index('idx_messages_created', 'created_at'),
    )
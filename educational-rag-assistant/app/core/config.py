# Настройки (Pydantic BaseSettings), env переменные
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Educational RAG Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: os.urandom(32).hex())
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # Database
    POSTGRES_USER: str = "educational_rag"
    POSTGRES_PASSWORD: str = "educational_rag_pass"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "educational_rag"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Qdrant
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "educational_documents"
    
    # OCR Settings
    OCR_MODEL_PATH: str = "./local_models/glm-ocr"
    OCR_CONFIDENCE_THRESHOLD: float = 0.5
    
    # Embedder Settings
    EMBEDDER_MODEL_NAME: str = "intfloat/e5-large-v2"
    EMBEDDER_MODEL_PATH: str = "./local_models/e5-large"
    EMBEDDING_DIMENSION: int = 1024
    
    # RAG Settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RESULTS: int = 5
    
    # Ollama Cloud
    OLLAMA_API_KEY: Optional[str] = None
    OLLAMA_MODEL: str = "llama2"
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
# Кастомные исключения
from typing import Any, Dict, Optional
from fastapi import HTTPException, status

class EducationalRAGException(Exception):
    """Базовое исключение для приложения"""
    def __init__(
        self,
        message: str,
        error_code: str = "internal_error",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class DocumentProcessingException(EducationalRAGException):
    """Исключение при обработке документов"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="document_processing_error",
            details=details
        )

class OCRException(EducationalRAGException):
    """Исключение при работе с OCR"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="ocr_error",
            details=details
        )

class EmbeddingException(EducationalRAGException):
    """Исключение при создании эмбеддингов"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="embedding_error",
            details=details
        )

class VectorStoreException(EducationalRAGException):
    """Исключение при работе с векторным хранилищем"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="vector_store_error",
            details=details
        )

class LLMException(EducationalRAGException):
    """Исключение при работе с LLM"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="llm_error",
            details=details
        )

class AuthenticationException(EducationalRAGException):
    """Исключение при аутентификации"""
    def __init__(self, message: str = "Could not validate credentials", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="authentication_error",
            details=details
        )

class AuthorizationException(EducationalRAGException):
    """Исключение при авторизации"""
    def __init__(self, message: str = "Not enough permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="authorization_error",
            details=details
        )

class ValidationException(EducationalRAGException):
    """Исключение при валидации данных"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="validation_error",
            details=details
        )

class NotFoundException(EducationalRAGException):
    """Исключение когда ресурс не найден"""
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="not_found",
            details=details
        )

# HTTP исключения для FastAPI
def http_exception_handler(exc: EducationalRAGException) -> HTTPException:
    """Преобразует наше исключение в HTTPException"""
    status_code_map = {
        "validation_error": status.HTTP_400_BAD_REQUEST,
        "authentication_error": status.HTTP_401_UNAUTHORIZED,
        "authorization_error": status.HTTP_403_FORBIDDEN,
        "not_found": status.HTTP_404_NOT_FOUND,
        "document_processing_error": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "ocr_error": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "embedding_error": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "vector_store_error": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "llm_error": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "internal_error": status.HTTP_500_INTERNAL_SERVER_ERROR
    }
    
    status_code = status_code_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return HTTPException(
        status_code=status_code,
        detail={
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )
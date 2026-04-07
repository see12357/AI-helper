# Загрузка PDF, удаление файлов
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.schemas.chat_schema import DocumentResponse
from app.services.pdf_processor import pdf_processor
from app.services.embedder import embedder
from app.core.security import get_current_user
import os
import uuid
from pathlib import Path

router = APIRouter(prefix="/documents", tags=["documents"])

# Upload directory
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    stored_filename = f"{file_id}{file_extension}"
    file_path = UPLOAD_DIR / stored_filename
    
    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Process PDF
    try:
        # Extract text
        text_content = await pdf_processor.extract_text(str(file_path))
        
        # If no text extracted, use OCR
        if not text_content.strip():
            from app.services.ocr_service import ocr_service
            text_content = await ocr_service.extract_text_with_ocr(str(file_path))
        
        # Generate embeddings
        embeddings = await embedder.generate_embeddings(text_content)
        
        # Save to database
        db_document = Document(
            id=file_id,
            filename=file.filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            file_size=len(content),
            user_id=current_user.id,
            text_content=text_content,
            embeddings=embeddings
        )
        
        db.add(db_document)
        await db.commit()
        await db.refresh(db_document)
        
        return DocumentResponse.from_orm(db_document)
        
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document).where(Document.user_id == current_user.id)
    )
    documents = result.scalars().all()
    return [DocumentResponse.from_orm(doc) for doc in documents]

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete file
    if Path(document.file_path).exists():
        Path(document.file_path).unlink()
    
    # Delete from database
    await db.delete(document)
    await db.commit()
    
    return {"message": "Document deleted successfully"}
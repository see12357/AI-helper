import asyncio
import io
import fitz  # PyMuPDF
from typing import List, Optional
import traceback
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Service for processing unstructured files (PDFs, Images) into extracted text.
    Handles OCR fallback for scanned pages using GLM OCR.
    """
    
    def __init__(self):
        # Mock GLM OCR model initialization
        # In actual implementation: self.ocr_model = load_glm_ocr_model()
        pass

    def _simulate_glm_ocr(self, image_bytes: bytes) -> str:
        """
        Simulated CPU-bound/GPU-bound operation for running GLM OCR inference.
        
        Args:
            image_bytes (bytes): The raw bytes of the image/page.
            
        Returns:
            str: Extracted text from the OCR.
        """
        # Mocking a slow ML inference call
        return " [Simulated GLM OCR Extracted Text] "

    def _extract_page_text(self, page: fitz.Page) -> str:
        """
        Extracts text from a PyMuPDF page. If the text is too short, falls back to OCR.
        This runs in a thread to prevent blocking the async loop.
        
        Args:
            page (fitz.Page): The PyMuPDF page object.
            
        Returns:
            str: The extracted text for the single page.
        """
        text = page.get_text("text").strip()
        if len(text) < 50:
            logger.info("Text < 50 chars, falling back to OCR.")
            # Convert page to image for OCR
            pix = page.get_pixmap()
            image_bytes = pix.tobytes("png")
            fallback_text = self._simulate_glm_ocr(image_bytes)
            return fallback_text
        return text

    def _process_pdf_sync(self, file_bytes: bytes) -> str:
        """
        Synchronous CPU-bound processing of a PDF file.
        Iterates over pages, extracts text or uses OCR.
        
        Args:
            file_bytes (bytes): The raw PDF file bytes.
            
        Returns:
            str: Combined extracted text from all pages.
        """
        full_text = []
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = self._extract_page_text(page)
                full_text.append(f"--- Page {page_num+1} ---\n{page_text}")
            doc.close()
            return "\n".join(full_text)
        except Exception as e:
            logger.error(f"Failed to process PDF: {str(e)}")
            logger.error(traceback.format_exc())
            raise ValueError(f"Failed to process PDF document: {str(e)}")

    def _process_image_sync(self, file_bytes: bytes) -> str:
        """
        Synchronous processing of an image using OCR.
        
        Args:
            file_bytes (bytes): Raw bytes of the image file.
            
        Returns:
            str: Extracted text from the OCR model.
        """
        try:
            return self._simulate_glm_ocr(file_bytes)
        except Exception as e:
            logger.error(f"Failed to process Image: {str(e)}")
            raise ValueError(f"Failed to process Image document: {str(e)}")

    async def process_file(self, file_bytes: bytes, mime_type: str) -> str:
        """
        Asynchronously processes a file by delegating CPU/GPU bound tasks to a thread pool.
        
        Args:
            file_bytes (bytes): The raw bytes of the file.
            mime_type (str): The MIME type of the file.
            
        Returns:
            str: The fully extracted textual content of the file.
        """
        supported_images = ["image/jpeg", "image/png", "image/jpg"]
        
        if mime_type == "application/pdf":
            # Run the heavy CPU-bound PyMuPDF and OCR operations in a background thread
            result = await asyncio.to_thread(self._process_pdf_sync, file_bytes)
            return result
        elif mime_type in supported_images:
            # Run the inference directly in a background thread
            result = await asyncio.to_thread(self._process_image_sync, file_bytes)
            return result
        else:
            raise ValueError(f"Unsupported mime-type: {mime_type}. Must be PDF or JPG/PNG.")

processor_service = DocumentProcessor()

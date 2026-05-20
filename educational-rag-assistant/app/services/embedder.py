import asyncio
import re
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchAny, MatchValue, PointStruct
import uuid
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service for chunking text, generating embeddings via SentenceTransformers,
    and upserting them into a Qdrant vector database.
    """
    
    def __init__(self):
        logger.info(f"Loading Embedding Model: {settings.EMBEDDER_MODEL_NAME}...")
        self.model = SentenceTransformer(settings.EMBEDDER_MODEL_NAME)
        logger.info("Embedding Model loaded successfully.")
        
        # Connect to async Qdrant client
        host = "localhost" if settings.QDRANT_HOST == "qdrant" else settings.QDRANT_HOST
        self.qdrant_client = AsyncQdrantClient(host=host, port=settings.QDRANT_PORT) 
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        
        # We assume the collection has been created with proper vector size (1024 for e5-large).
        # We would create it if it didn't exist here.

    def _chunk_text_sync(self, text: str) -> List[str]:
        """
        Synchronous CPU operation for chunking text.
        
        Args:
            text (str): The extracted text.
            
        Returns:
            List[str]: A list of text chunks.
        """
        # Using recursive character splitter from langchain
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # ~500 tokens / words / chars based on param usage; often characters, adjust depending on tokenizer.
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        return splitter.split_text(text)

    def _chunk_text_with_pages_sync(self, text: str) -> List[Dict[str, str]]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        page_matches = list(re.finditer(r"--- Page\s+(\d+)\s+---", text))
        page_sections = []

        if page_matches:
            prefix = text[:page_matches[0].start()].strip()
            for index, match in enumerate(page_matches):
                page_number = match.group(1)
                start = match.end()
                end = page_matches[index + 1].start() if index + 1 < len(page_matches) else len(text)
                page_text = text[start:end].strip()
                if prefix:
                    page_text = f"{prefix}\n{page_text}"
                page_sections.append((page_number, page_text))
        else:
            page_sections.append(("1", text))

        chunks = []
        for page_number, page_text in page_sections:
            for chunk in splitter.split_text(page_text):
                chunks.append({"text": chunk, "page_number": page_number})
        return chunks

    def _generate_embeddings_sync(self, texts: List[str]) -> List[List[float]]:
        """
        Synchronous ML inference operation to generate embeddings using E5 localized model.
        
        Args:
            texts (List[str]): List of string chunks to embed.
            
        Returns:
            List[List[float]]: The corresponding vector embeddings.
        """
        if hasattr(self, "model") and self.model is not None:
            # E5 specifically requires 'passage: ' prefixes for indexed documents
            prefixed_texts = ["passage: " + t for t in texts]
            # normalize_embeddings=True is recommended for e5 models for cosine similarity
            return self.model.encode(prefixed_texts, normalize_embeddings=True).tolist()
            
        # Fallback just in case
        return [[0.01 * j for j in range(settings.EMBEDDING_DIMENSION)] for _ in texts]

    def _generate_query_embedding_sync(self, text: str) -> List[float]:
        if hasattr(self, "model") and self.model is not None:
            return self.model.encode("query: " + text, normalize_embeddings=True).tolist()

        return [0.01 * j for j in range(settings.EMBEDDING_DIMENSION)]

    async def process_and_upsert(self, text: str, user_id: str, document_id: str, filename: str | None = None) -> None:
        """
        Main pipeline to chunk text, create embeddings, and upsert into Qdrant.
        Runs CPU/GPU bounds in separate threads.
        
        Args:
            text (str): Full text of the document.
            user_id (str): ID of the user.
            document_id (str): ID of the document.
        """
        try:
            # 1. Chunking
            chunks = await asyncio.to_thread(self._chunk_text_with_pages_sync, text)
            
            # 2. Embedding Generation
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = await asyncio.to_thread(self._generate_embeddings_sync, chunk_texts)
            
            # 3. Upsert to Vector Database
            await self._upsert_vectors(
                chunks=chunks,
                embeddings=embeddings,
                user_id=user_id,
                document_id=document_id,
                filename=filename or document_id,
            )
            logger.info(f"Successfully upserted {len(chunks)} chunks for doc {document_id}")
        except Exception as e:
            logger.error(f"Failed to process and upsert embeddings: {str(e)}")
            raise

    async def _upsert_vectors(
        self,
        chunks: List[Dict[str, str]],
        embeddings: List[List[float]],
        user_id: str,
        document_id: str,
        filename: str,
    ) -> None:
        """
        Upserts vector points structure into the asynchronous Qdrant client.
        """
        if not getattr(self, "_collection_checked", False):
            if not await self.qdrant_client.collection_exists(self.collection_name):
                from qdrant_client.models import Distance, VectorParams
                await self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=settings.EMBEDDING_DIMENSION, distance=Distance.COSINE),
                )
            self._collection_checked = True

        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            page_info = chunk.get("page_number", "1")
            chunk_text = chunk.get("text", "")
            
            payload = {
                "user_id": user_id,
                "document_id": document_id,
                "filename": filename,
                "page_number": page_info,
                "chunk_text": chunk_text
            }
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            )

        # Upsert operation to qdrant using asyncpg client equivalently.
        await self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    async def search_relevant_chunks(
        self,
        query: str,
        user_id: str,
        document_id: str | None = None,
        document_ids: List[str] | None = None,
        limit: int = 5,
    ) -> List[Dict[str, str]]:
        """
        Search Qdrant for chunks relevant to the current user's question.
        """
        if not await self.qdrant_client.collection_exists(self.collection_name):
            return []

        query_vector = await asyncio.to_thread(self._generate_query_embedding_sync, query)
        filters = [
            FieldCondition(
                key="user_id",
                match=MatchValue(value=user_id),
            )
        ]
        scoped_document_ids = document_ids or ([document_id] if document_id else [])
        if scoped_document_ids:
            filters.append(
                FieldCondition(
                    key="document_id",
                    match=MatchAny(any=scoped_document_ids),
                )
            )

        result = await self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=Filter(must=filters),
            limit=limit,
            with_payload=True,
        )

        chunks = []
        for point in result.points:
            payload = point.payload or {}
            chunk_text = payload.get("chunk_text")
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "document_id": payload.get("document_id", ""),
                    "filename": payload.get("filename", "Документ"),
                    "page_number": str(payload.get("page_number", "1")),
                })

        return chunks

embedder_service = EmbeddingService()

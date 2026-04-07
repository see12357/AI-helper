import logging
from typing import List, Union
import numpy as np
from app.core.exceptions import EmbedderException
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbedderService:
    def __init__(self):
        self.model_name = settings.EMBEDDER_MODEL_NAME
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the E5-large embedding model"""
        try:
            # TODO: Implement actual E5-large model loading
            # For now, we'll simulate the model loading
            logger.info(f"Loading E5-large embedder model: {self.model_name}")
            # In a real implementation, you would load the model here
            # Example: self.model = SentenceTransformer(self.model_name)
            self.model = "simulated_model"  # Placeholder
            logger.info("E5-large embedder model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load E5-large embedder model: {str(e)}")
            raise EmbedderException(f"Failed to load embedder model: {str(e)}")
    
    def encode_text(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        Encode text(s) into embeddings using E5-large
        
        Args:
            texts: Single text string or list of text strings
            
        Returns:
            List of embeddings (each embedding is a list of floats)
        """
        try:
            if not self.model:
                raise EmbedderException("Embedder model not loaded")
            
            # Convert single text to list for uniform processing
            if isinstance(texts, str):
                texts = [texts]
            
            logger.info(f"Encoding {len(texts)} text(s)")
            
            # TODO: Implement actual text encoding
            # For now, we'll simulate the encoding
            # In a real implementation, you would use the model to encode text
            # Example: embeddings = self.model.encode(texts)
            
            # Simulate embeddings (768-dimensional for E5-large)
            embeddings = []
            for text in texts:
                # Generate deterministic but varied embeddings based on text hash
                import hashlib
                text_hash = hashlib.md5(text.encode()).hexdigest()
                # Use hash to generate consistent pseudo-random values
                seed = int(text_hash[:8], 16)
                np.random.seed(seed)
                embedding = np.random.rand(768).tolist()  # E5-large produces 768-dim embeddings
                embeddings.append(embedding)
            
            logger.info(f"Text encoding completed. Generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to encode text: {str(e)}")
            raise EmbedderException(f"Text encoding failed: {str(e)}")
    
    def encode_single_text(self, text: str) -> List[float]:
        """
        Encode a single text into an embedding
        
        Args:
            text: Text string to encode
            
        Returns:
            Embedding as a list of floats
        """
        embeddings = self.encode_text([text])
        return embeddings[0] if embeddings else []
    
    def is_available(self) -> bool:
        """Check if the embedder service is available"""
        return self.model is not None
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings produced by the model"""
        return 768  # E5-large produces 768-dimensional embeddings
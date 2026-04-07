import logging
import json
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
from app.core.exceptions import LLMException
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # Hardcoded to match requirements
        self.model_name = "gemini-3-flash-preview:cloud"
        self.base_url = "http://localhost:11434"
        self.api_generate_url = f"{self.base_url}/api/generate"
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate_response(self, prompt: str, context: Optional[List[str]] = None, 
                         temperature: float = 0.7, max_tokens: int = 500) -> str:
        """
        Generate a non-streaming response using the local Ollama API
        """
        try:
            full_prompt = prompt
            if context:
                context_text = "\n\n".join(context)
                full_prompt = f"Context:\n{context_text}\n\nQuestion: {prompt}"
            
            logger.info(f"Generating block response with Ollama model '{self.model_name}' on localhost")
            
            payload = {
                "model": self.model_name,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            response = await self.client.post(self.api_generate_url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data.get("response", "")
            
        except Exception as e:
            logger.error(f"Failed to generate LLM response: {str(e)}")
            raise LLMException(f"LLM response generation failed: {str(e)}")
    
    async def generate_streaming_response(self, prompt: str, context: Optional[List[str]] = None,
                                  temperature: float = 0.7, max_tokens: int = 500) -> AsyncGenerator[str, None]:
        """
        Generate an asynchronous streaming response using the local Ollama API
        """
        full_prompt = prompt
        if context:
            context_text = "\n\n".join(context)
            full_prompt = f"Context:\n{context_text}\n\nQuestion: {prompt}"
        
        logger.info(f"Generating streaming response with Ollama model '{self.model_name}' on localhost")
        
        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            async with self.client.stream("POST", self.api_generate_url, json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk
                        
                        if data.get("done"):
                            break
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON from Ollama stream line: {line}")
                        
        except Exception as e:
            logger.error(f"Failed to stream from Ollama API on localhost: {str(e)}")
            raise LLMException(f"Streaming LLM response generation failed: {str(e)}")
            
    async def is_available(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

llm_service = LLMService()
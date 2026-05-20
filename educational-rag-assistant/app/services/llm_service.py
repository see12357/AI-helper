import logging
import json
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
from app.core.exceptions import LLMException
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.model_name = settings.OLLAMA_MODEL
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.api_generate_url = f"{self.base_url}/api/generate"
        self.client = httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS)

    def _prepare_prompt(self, prompt: str, context: Optional[List[str]] = None) -> str:
        full_prompt = prompt
        if context:
            context_text = "\n\n".join(context)
            full_prompt = f"Context:\n{context_text}\n\nQuestion: {prompt}"

        if self.model_name.lower().startswith("qwen"):
            return f"/no_think\n{full_prompt}"

        return full_prompt
    
    async def generate_response(self, prompt: str, context: Optional[List[str]] = None, 
                         temperature: float = 0.7, max_tokens: int | None = None) -> str:
        """
        Generate a non-streaming response using the local Ollama API
        """
        try:
            full_prompt = self._prepare_prompt(prompt, context)
            
            logger.info(
                "Generating block response with Ollama model '%s' at %s",
                self.model_name,
                self.base_url,
            )
            
            payload = {
                "model": self.model_name,
                "prompt": full_prompt,
                "stream": False,
                "think": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens or settings.OLLAMA_MAX_TOKENS
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
                                  temperature: float = 0.7, max_tokens: int | None = None) -> AsyncGenerator[str, None]:
        """
        Generate an asynchronous streaming response using the local Ollama API
        """
        full_prompt = self._prepare_prompt(prompt, context)
        
        logger.info(
            "Generating streaming response with Ollama model '%s' at %s",
            self.model_name,
            self.base_url,
        )
        
        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": True,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or settings.OLLAMA_MAX_TOKENS
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
            logger.error("Failed to stream from Ollama API at %s: %s", self.base_url, str(e))
            raise LLMException(f"Streaming LLM response generation failed: {str(e)}")
            
    async def is_available(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

llm_service = LLMService()

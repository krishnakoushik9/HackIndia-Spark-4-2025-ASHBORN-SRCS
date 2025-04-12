import json
import requests
import logging
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Client for interacting with Ollama LLM
    """
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.base_url = "http://localhost:11434/api"
        self.model_name = model_name
        
        # Ensure model is available
        self._ensure_model()
    
    def _ensure_model(self):
        """Check if model is available and pull if not"""
        try:
            # List available models
            response = requests.get(f"{self.base_url}/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                available_models = [m["name"] for m in models]
                
                if self.model_name not in available_models:
                    logger.info(f"Model {self.model_name} not found. Pulling...")
                    self._pull_model()
                else:
                    logger.info(f"Model {self.model_name} already available")
            else:
                logger.warning("Failed to check models, will attempt to use anyway")
        except Exception as e:
            logger.error(f"Error checking models: {str(e)}")
    
    def _pull_model(self):
        """Pull model from Ollama"""
        try:
            response = requests.post(
                f"{self.base_url}/pull",
                json={"name": self.model_name}
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully pulled model {self.model_name}")
                return True
            else:
                logger.error(f"Failed to pull model: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error pulling model: {str(e)}")
            return False
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for text
        """
        try:
            # Clean and truncate text
            if not text or not text.strip():
                text = "empty document"
            
            text = text[:10000]  # Limit text length
            
            response = requests.post(
                f"{self.base_url}/embeddings",
                json={"model": self.model_name, "prompt": text}
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("embedding", [])
            else:
                logger.error(f"Embedding API error: {response.text}")
                # Return empty vector as fallback
                return [0.0] * 768
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            # Return empty vector as fallback
            return [0.0] * 768
    
    async def generate_summary(self, file_path: str, content: str, query_context: str = None, max_length: int = 300) -> str:
        """
        Generate a summary for a document
        """
        try:
            # Prepare prompt based on whether this is a query-focused summary
            if query_context:
                prompt = f"""Summarize the following document content in relation to the query: "{query_context}"
                
Content from file: {file_path}

{content[:3000]}

Provide a concise summary in less than {max_length} characters that's relevant to the query.
"""
            else:
                prompt = f"""Provide a concise summary of the following document:
                
File: {file_path}

{content[:3000]}

Create a clear and informative summary in less than {max_length} characters.
"""
            
            # Send request to Ollama
            response = requests.post(
                f"{self.base_url}/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.95,
                        "max_tokens": max(100, max_length // 3)
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get("response", "")
                
                # Clean up the summary
                summary = summary.strip()
                if len(summary) > max_length:
                    summary = summary[:max_length-3] + "..."
                
                return summary
            else:
                logger.error(f"Summary generation error: {response.text}")
                return "Summary generation failed."
                
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return "Error generating summary."
    
    async def answer_question(self, question: str, context: str) -> str:
        """
        Answer a question based on document context
        """
        try:
            # Prepare RAG prompt
            prompt = f"""Answer the following question based on the provided document content:

Question: {question}

Document Content:
{context[:4000]}

Provide a clear, factual answer based only on the information in the document. If the document doesn't contain information to answer the question, simply state that.
"""
            
            # Send request to Ollama
            response = requests.post(
                f"{self.base_url}/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "top_p": 0.95,
                        "max_tokens": 500
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("response", "")
                return answer.strip()
            else:
                logger.error(f"Question answering error: {response.text}")
                return "Failed to answer question."
                
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return "Error processing your question."
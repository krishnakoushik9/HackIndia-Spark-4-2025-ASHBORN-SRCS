from fastapi import FastAPI, Query, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio
import subprocess
import uvicorn
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import requests

from document_processor import DocumentProcessor
from vector_store import VectorStore
from llm_client import LLMClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Document Search & Retrieval Assistant")

# Replace your existing CORS middleware with this one
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Make sure POST is included
    allow_headers=["*"],
)
# Add this to your app.py file

# Add this to your Pydantic models
class ChatRequest(BaseModel):
    query: str

@app.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """Respond to user messages using the LLM"""
    try:
        if not llm_client:
            raise HTTPException(status_code=500, detail="LLM client not initialized")
        
        # Process the user query
        response_text = await process_chat_request(request.query)
        
        return {"response": response_text}
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

async def process_chat_request(query: str) -> str:
    
    try:
       
        prompt = f"""You are a helpful, concise AI assistant with name ASHBORN AI. 
        Answer the following question directly and briefly, without links, disclaimers, or unnecessary text.
        Keep your responses short and to the point. Don't add unnecessary context or explanations.
        
        {query}
        """
        
      
        response = requests.post(
            f"{llm_client.base_url}/generate",
            json={
                "model": llm_client.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.9,
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
            logger.error(f"LLM response error: {response.text}")
            return "I encountered an error processing your request."
            
    except Exception as e:
        logger.error(f"Chat processing error: {str(e)}")
        return "Sorry, I'm having trouble answering right now."

# Pydantic models
class IndexRequest(BaseModel):
    folders: List[str]

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

class SummaryRequest(BaseModel):
    file_path: str

class RelatedRequest(BaseModel):
    file_path: str
    limit: int = 3

class OpenFileRequest(BaseModel):
    file_path: str

# Application state
vector_store = None
doc_processor = None
llm_client = None
indexed_folders = []

@app.on_event("startup")
async def startup_event():
    global vector_store, doc_processor, llm_client
    logger.info("Starting backend services...")
    
    # Check if Ollama is running and start if needed
    try:
        subprocess.run(["ollama", "list"], check=True, capture_output=True)
        logger.info("Ollama is running")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("Ollama not running or not found. Starting Ollama...")
        try:
            # Start Ollama in background
            subprocess.Popen(["ollama", "serve"], 
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            await asyncio.sleep(5)  # Give it time to start
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
    
    # Initialize components
    llm_client = LLMClient(model_name="gemma3:1b")
    vector_store = VectorStore()
    doc_processor = DocumentProcessor(vector_store, llm_client)
    
    logger.info("Backend services initialized successfully")

@app.get("/status")
async def status():
    """Check if backend is running"""
    return {"status": "online", "indexed_folders": indexed_folders}

@app.post("/index")
async def index_folders(request: IndexRequest):
    """Index documents from specified folders"""
    global indexed_folders
    
    if not request.folders:
        raise HTTPException(status_code=400, detail="No folders provided")
    
    # Validate folder paths
    invalid_folders = [f for f in request.folders if not os.path.isdir(f)]
    if invalid_folders:
        raise HTTPException(status_code=400, 
                          detail=f"Invalid folders: {invalid_folders}")
    
    try:
        # Reset index if folders have changed
        if set(indexed_folders) != set(request.folders):
            vector_store.reset()
            
        # Process and index documents
        file_count = await doc_processor.process_folders(request.folders)
        indexed_folders = request.folders
        
        return {
            "status": "success", 
            "indexed_files": file_count, 
            "folders": request.folders
        }
    except Exception as e:
        logger.error(f"Indexing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

@app.post("/search")
async def search_documents(request: SearchRequest):
    """Search for documents using natural language query"""
    if not indexed_folders:
        raise HTTPException(status_code=400, 
                          detail="No folders indexed. Please index folders first.")
    
    try:
        results = await vector_store.search(request.query, limit=request.limit)
        
        # Enhance results with summaries
        enhanced_results = []
        for result in results:
            file_path = result["file_path"]
            snippet = result.get("snippet", "")
            
            # Generate a quick summary for the search result context
            mini_summary = await llm_client.generate_summary(
                file_path=file_path, 
                content=snippet,
                query_context=request.query,
                max_length=150
            )
            
            enhanced_results.append({
                "file_path": file_path,
                "score": result["score"],
                "summary": mini_summary,
                "snippet": snippet,
                "metadata": result.get("metadata", {})
            })
            
        return {"results": enhanced_results}
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/summary")
async def get_summary(request: SummaryRequest):
    """Generate summary for a specific document"""
    if not os.path.isfile(request.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Extract content
        content = await doc_processor.extract_text(request.file_path)
        print(f"[DEBUG] Extracted content (first 300 chars):\n{content[:300]}")

        # Generate summary
        summary = await llm_client.generate_summary(
            file_path=request.file_path,
            content=content,
            max_length=500
        )
        print(f"[DEBUG] Generated summary:\n{summary}")

        return {"file_path": request.file_path, "summary": summary}
    except Exception as e:
        logger.error(f"Summary error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Summary failed: {str(e)}")

@app.post("/related")
async def get_related(request: RelatedRequest):
    """Find related documents to a specific file"""
    if not os.path.isfile(request.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Get file content
        content = await doc_processor.extract_text(request.file_path)
        
        # Use content to find similar documents
        results = await vector_store.search_by_content(
            content=content,
            limit=request.limit + 1  # +1 to account for the file itself
        )
        
        # Filter out the original file
        related = [r for r in results if r["file_path"] != request.file_path][:request.limit]
        
        # Add mini summaries
        for item in related:
            item["summary"] = await llm_client.generate_summary(
                file_path=item["file_path"],
                content=item.get("snippet", ""),
                max_length=100
            )
        
        return {"file_path": request.file_path, "related": related}
    except Exception as e:
        logger.error(f"Related docs error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Finding related docs failed: {str(e)}")

@app.post("/open")
async def open_file(request: OpenFileRequest):
    """Open a file with the default system application"""
    if not os.path.isfile(request.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Use platform-specific commands to open file
        if os.name == 'nt':  # Windows
            os.startfile(request.file_path)
        elif os.name == 'posix':  # Linux/Mac
            if os.uname().sysname == 'Darwin':  # macOS
                subprocess.call(('open', request.file_path))
            else:  # Linux
                subprocess.call(('xdg-open', request.file_path))
                
        return {"status": "success", "file_path": request.file_path}
    except Exception as e:
        logger.error(f"File open error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Opening file failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8001)
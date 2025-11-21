"""
Embedding service adapter
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List

import torch
from sentence_transformers import SentenceTransformer

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    """Embedding service implementation with async support"""
    
    def __init__(self):
        self.model_name = settings.embedding_model
        logger.info(f"🔧 Inicjalizacja EmbeddingService z modelem: {self.model_name}")
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(self.model_name, device=device)
        
        if device == "cuda":
            logger.info(f"✅ Retriever (embedding) działa na GPU: {torch.cuda.get_device_name(0)}")
        else:
            logger.info("ℹ️  Retriever (embedding) działa na CPU")
        
        # Use thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text (async)"""
        logger.debug(f"🔍 Generowanie embedding dla tekstu (długość: {len(text)} znaków)")
        
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            self.executor,
            lambda: self.model.encode(text, convert_to_numpy=True)
        )
        
        logger.debug(f"✅ Embedding wygenerowany (wymiar: {len(embedding)})")
        return embedding.tolist()
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (async)"""
        logger.info(f"🔍 Generowanie embeddings dla {len(texts)} tekstów")
        
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            self.executor,
            lambda: self.model.encode(texts, convert_to_numpy=True)
        )
        
        logger.info(f"✅ Wygenerowano {len(embeddings)} embeddings (wymiar: {len(embeddings[0]) if embeddings else 0})")
        return [emb.tolist() for emb in embeddings]


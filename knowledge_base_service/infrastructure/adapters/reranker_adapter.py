"""
Reranker adapter for improving search results ranking
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import torch
from sentence_transformers import CrossEncoder

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RerankerService:
    """Reranker service implementation with async support"""
    
    def __init__(self):
        self.model_name = getattr(settings, 'reranker_model', 'sdadas/polish-reranker-roberta-v3')
        self.enabled = getattr(settings, 'reranker_enabled', True)  # Domyślnie włączony
        self.score_threshold = getattr(settings, 'reranker_score_threshold', 0.0)
        self.max_length = getattr(settings, 'reranker_max_length', 512)
        self.batch_size = getattr(settings, 'reranker_batch_size', 4)
        
        logger.info(f"🔧 Inicjalizacja RerankerService")
        logger.info(f"   Model: {self.model_name}")
        logger.info(f"   Włączony: {self.enabled}")
        logger.info(f"   Próg score: {self.score_threshold}")
        logger.info(f"   Max length: {self.max_length}")
        logger.info(f"   Batch size: {self.batch_size}")
        
        self.model: Optional[CrossEncoder] = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        
        # Lazy loading - model will be loaded on first use
        self._model_loaded = False
    
    def _load_model(self):
        """Load reranker model (synchronous)"""
        if self._model_loaded:
            return
        
        if not self.enabled:
            logger.info("ℹ️  Reranking wyłączony - pomijam ładowanie modelu")
            return
        
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"📥 Ładowanie modelu rerankingu: {self.model_name}")
            
            model_kwargs = {}
            if device == "cuda":
                model_kwargs["torch_dtype"] = torch.float16
            
            self.model = CrossEncoder(
                self.model_name,
                device=device,
                max_length=self.max_length,
                trust_remote_code=True,
                model_kwargs=model_kwargs
            )
            self._model_loaded = True
            
            if device == "cuda":
                logger.info(f"✅ Reranker działa na GPU: {torch.cuda.get_device_name(0)}")
            else:
                logger.info("ℹ️  Reranker działa na CPU")
                
        except Exception as e:
            logger.error(f"❌ Błąd podczas ładowania modelu rerankingu: {str(e)}", exc_info=True)
            logger.warning(f"   Reranking będzie wyłączony")
            self.enabled = False
            self.model = None
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        scores: Optional[List[float]] = None
    ) -> List[tuple[str, float]]:
        """
        Rerank documents based on query
        
        Args:
            query: Search query
            documents: List of document contents
            scores: Optional initial scores (for filtering)
        
        Returns:
            List of tuples (document, reranked_score) sorted by score descending
        """
        if not self.enabled or not documents:
            # If reranking is disabled, return original documents with original scores
            if scores:
                return list(zip(documents, scores))
            return list(zip(documents, [0.0] * len(documents)))
        
        # Lazy load model
        if not self._model_loaded:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self._load_model)
        
        if not self.model:
            # Model failed to load, return original
            if scores:
                return list(zip(documents, scores))
            return list(zip(documents, [0.0] * len(documents)))
        
        try:
            logger.info(f"🔄 Rozpoczynam reranking dla {len(documents)} dokumentów")
            
            # Prepare pairs for reranking
            pairs = [[query, doc] for doc in documents]
            
            # Rerank in batches to avoid memory issues
            reranked_scores = []
            loop = asyncio.get_event_loop()
            total_batches = (len(pairs) + self.batch_size - 1) // self.batch_size
            
            for i in range(0, len(pairs), self.batch_size):
                batch = pairs[i:i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                
                logger.debug(f"   Przetwarzam batch {batch_num}/{total_batches} ({len(batch)} par)")
                
                # Run prediction in executor to avoid blocking
                if self.model is None:
                    # Model not loaded, return original scores
                    logger.warning("   ⚠️  Model nie jest załadowany - zwracam oryginalne score")
                    if scores:
                        return list(zip(documents, scores))
                    return list(zip(documents, [0.0] * len(documents)))
                
                # Type guard - model is not None here
                model = self.model
                batch_scores = await loop.run_in_executor(
                    self.executor,
                    lambda b=batch, m=model: m.predict(b).tolist()
                )
                
                reranked_scores.extend(batch_scores)
                logger.debug(f"   ✅ Batch {batch_num} przetworzony (scores: {[f'{s:.3f}' for s in batch_scores]})")
                
                # Clear GPU cache after each batch (if using GPU)
                if torch.cuda.is_available():
                    await loop.run_in_executor(
                        self.executor,
                        torch.cuda.empty_cache
                    )
            
            # Combine documents with reranked scores
            results = list(zip(documents, reranked_scores))
            
            # Filter by threshold and sort by score descending
            filtered_results = [
                (doc, score) for doc, score in results
                if score >= self.score_threshold
            ]
            
            # Sort by score descending
            filtered_results.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"✅ Reranking zakończony")
            logger.info(f"   Przed filtrowaniem: {len(results)} dokumentów")
            logger.info(f"   Po filtrowaniu (threshold={self.score_threshold}): {len(filtered_results)} dokumentów")
            if filtered_results:
                logger.info(f"   Najlepszy score: {filtered_results[0][1]:.4f}")
                logger.info(f"   Najgorszy score: {filtered_results[-1][1]:.4f}")
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"❌ Błąd podczas rerankingu: {str(e)}", exc_info=True)
            # Return original documents with original scores on error
            if scores:
                logger.warning("   Zwracam oryginalne score zamiast rerankingu")
                return list(zip(documents, scores))
            return list(zip(documents, [0.0] * len(documents)))
    
    def is_enabled(self) -> bool:
        """Check if reranking is enabled"""
        return self.enabled and self._model_loaded


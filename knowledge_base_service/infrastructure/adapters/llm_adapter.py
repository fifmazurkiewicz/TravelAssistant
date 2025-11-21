"""
LLM adapter for generating responses using OpenRouter/Gemini
"""
import logging
from typing import List, Optional

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from config import get_settings

logger = logging.getLogger(__name__)


class LLMAdapter:
    """Adapter for LLM communication via OpenRouter"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize LLM adapter
        
        Args:
            api_key: OpenRouter API key (if None, uses settings)
            base_url: OpenRouter base URL (if None, uses settings)
            model: LLM model to use (if None, uses settings)
        """
        if AsyncOpenAI is None:
            raise ImportError("openai package is required. Install with: pip install openai")
        
        # Load settings dynamically to get latest values from .env
        settings = get_settings()
        
        # Get the .env file path from config
        import config
        env_path = config.ENV_FILE_PATH if hasattr(config, 'ENV_FILE_PATH') and config.ENV_FILE_PATH.exists() else None
        
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = base_url or settings.openrouter_base_url
        self.model = model or getattr(settings, 'llm_model', 'google/gemini-2.5-flash-lite-preview-09-2025')
        
        if not self.api_key:
            logger.warning("No OpenRouter API key provided. LLM responses will be disabled.")
            if env_path:
                logger.warning(f"Expected .env file location: {env_path}")
            logger.warning("Make sure OPENROUTER_API_KEY is set in the .env file in the PROJECT ROOT directory")
            logger.warning("(Not in knowledge_base_service folder, but in the main TravelAssistant folder)")
            logger.warning("Format: OPENROUTER_API_KEY=sk-or-v1-... (no spaces around =)")
            self.client = None
        else:
            # Mask API key in logs (show only first 8 chars)
            masked_key = self.api_key[:8] + "..." if len(self.api_key) > 8 else "***"
            logger.info(f"OpenRouter API key loaded (key: {masked_key})")
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
    
    async def generate_response(
        self,
        user_query: str,
        context_documents: List[dict],
        conversation_history: Optional[List[dict]] = None
    ) -> str:
        """
        Generate response to user query based on context documents
        
        Args:
            user_query: User's question
            context_documents: List of documents from search results with 'content' and optional 'metadata'
            conversation_history: Previous conversation messages (optional)
            
        Returns:
            Generated response text
        """
        if not self.client:
            return "Przepraszam, ale funkcja generowania odpowiedzi przez LLM nie jest dostępna. Brak klucza API OpenRouter."
        
        # Build context from documents
        context_text = self._build_context(context_documents)
        
        # Log context for debugging
        logger.info(f"📝 Generowanie odpowiedzi LLM")
        logger.info(f"   Query: {user_query[:100]}..." if len(user_query) > 100 else f"   Query: {user_query}")
        logger.info(f"   Liczba dokumentów kontekstowych: {len(context_documents)}")
        if context_documents:
            logger.debug(f"   Pierwszy dokument (pierwsze 200 znaków): {context_documents[0].get('content', '')[:200]}...")
        if conversation_history:
            logger.info(f"   Historia konwersacji: {len(conversation_history)} wiadomości")
            for idx, msg in enumerate(conversation_history[-3:], 1):  # Log last 3 messages
                role = msg.get("role", "unknown")
                content_preview = msg.get("content", "")[:50] + "..." if len(msg.get("content", "")) > 50 else msg.get("content", "")
                logger.debug(f"      {idx}. {role}: {content_preview}")
        
        # Build prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_query, context_text)
        
        try:
            # Build messages list in correct order:
            # 1. System prompt
            # 2. Conversation history (if any)
            # 3. Current user query with context
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation history BEFORE current query (if provided)
            if conversation_history:
                # Add all history messages (they should already exclude current query)
                for msg in conversation_history:
                    if msg.get("role") in ["user", "assistant"]:
                        content = msg.get("content", "")
                        if content:  # Only add non-empty messages
                            messages.append({
                                "role": msg["role"],
                                "content": content
                            })
            
            # Add current user query with context (always last)
            messages.append({"role": "user", "content": user_prompt})
            
            logger.debug(f"   Wysyłam {len(messages)} wiadomości do LLM (system + {len(conversation_history) if conversation_history else 0} historia + 1 aktualne pytanie)")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                temperature=0.7,
                max_tokens=2000  # Zwiększony limit dla dłuższych odpowiedzi z kontekstem
            )
            
            content = response.choices[0].message.content
            response_text = content.strip() if content else "Przepraszam, nie udało się wygenerować odpowiedzi."
            
            logger.info(f"✅ Odpowiedź LLM wygenerowana (długość: {len(response_text)} znaków)")
            logger.debug(f"   Odpowiedź (pierwsze 200 znaków): {response_text[:200]}...")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}", exc_info=True)
            return f"Przepraszam, wystąpił błąd podczas generowania odpowiedzi: {str(e)}"
    
    def _build_context(self, documents: List[dict]) -> str:
        """Build context string from search results"""
        if not documents:
            return "Brak dostępnych dokumentów w bazie wiedzy."
        
        context_parts = []
        for idx, doc in enumerate(documents, 1):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            
            # Build document entry
            doc_entry = f"[Dokument {idx}]"
            if metadata.get("filename"):
                doc_entry += f" Źródło: {metadata.get('filename')}"
            if metadata.get("document_id"):
                doc_entry += f" (ID: {metadata.get('document_id')})"
            
            # Increase content length limit to 2000 chars for better context
            doc_entry += f"\n{content[:2000]}"
            if len(content) > 2000:
                doc_entry += "..."
            
            context_parts.append(doc_entry)
        
        return "\n\n".join(context_parts)
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for LLM"""
        return """Jesteś pomocnym asystentem podróży. Twoim zadaniem jest odpowiadać na pytania użytkowników na podstawie dostępnych dokumentów z bazy wiedzy oraz historii konwersacji.

Zasady:
1. Odpowiadaj na podstawie informacji zawartych w dostarczonych dokumentach oraz historii konwersacji
2. Jeśli informacja nie jest dostępna w dokumentach ani w historii, powiedz to jasno
3. Odpowiadaj w języku polskim, naturalnie i przyjaźnie
4. Strukturyzuj odpowiedzi, używając punktów lub krótkich akapitów
5. Jeśli dokumenty zawierają konkretne liczby, daty lub fakty, użyj ich dokładnie
6. Nie wymyślaj informacji, których nie ma w dokumentach ani w historii konwersacji
7. Jeśli pytanie dotyczy konkretnego miejsca, skup się na informacjach z dokumentów dotyczących tego miejsca
8. Wykorzystuj historię konwersacji jako kontekst - możesz odwoływać się do wcześniejszych pytań i odpowiedzi
9. Jeśli użytkownik zadaje pytanie powiązane z poprzednimi, użyj zarówno dokumentów jak i historii konwersacji do udzielenia pełnej odpowiedzi"""
    
    def _build_user_prompt(
        self,
        user_query: str,
        context_text: str
    ) -> str:
        """Build user prompt with context"""
        prompt = f"""Na podstawie poniższych dokumentów z bazy wiedzy oraz historii konwersacji (jeśli dostępna), odpowiedz na pytanie użytkownika.

AKTUALNE PYTANIE UŻYTKOWNIKA:
{user_query}

DOSTĘPNE DOKUMENTY Z BAZY WIEDZY:
{context_text}

INSTRUKCJE:
- Odpowiedz na pytanie: "{user_query}"
- Użyj informacji z powyższych dokumentów oraz z historii konwersacji (jeśli jest dostępna)
- Jeśli pytanie jest powiązane z wcześniejszymi pytaniami z historii, możesz odwołać się do nich
- Jeśli dokumenty nie zawierają odpowiedzi, sprawdź czy informacja nie była już omówiona w historii konwersacji
- Jeśli informacja nie jest dostępna ani w dokumentach ani w historii, powiedz to jasno
- Odpowiadaj w sposób naturalny i pomocny, wykorzystując cały dostępny kontekst

Odpowiedz na pytanie użytkownika w sposób naturalny i pomocny, wykorzystując zarówno dokumenty jak i historię konwersacji."""
        
        return prompt


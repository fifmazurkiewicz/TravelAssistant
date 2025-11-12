"""
Text cleaning utilities
"""
import re
from typing import Optional


class TextCleaner:
    """Utility class for cleaning text data"""
    
    @staticmethod
    def clean_html(html: str) -> str:
        """Remove HTML tags and clean text"""
        if not html:
            return ""
        
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        
        # Decode HTML entities (simplified)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    @staticmethod
    def remove_extra_whitespace(text: str) -> str:
        """Remove extra whitespace from text"""
        if not text:
            return ""
        return ' '.join(text.split())
    
    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """General text cleaning"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = TextCleaner.remove_extra_whitespace(text)
        
        # Remove special characters that might cause issues
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()
    
    @staticmethod
    def extract_numbers(text: str) -> Optional[float]:
        """Extract first number from text"""
        if not text:
            return None
        
        # Find first number (including decimals)
        match = re.search(r'\d+\.?\d*', text.replace(',', ''))
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        
        return None


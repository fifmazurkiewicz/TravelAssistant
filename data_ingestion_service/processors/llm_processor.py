"""
LLM-based data processor for analyzing and structuring travel data
"""
import json
import logging
from typing import Any, Dict, List, Optional

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

logger = logging.getLogger(__name__)


class LLMProcessor:
    """Process and structure travel data using LLM"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "openrouter/anthropic/claude-3-haiku"
    ):
        """
        Initialize LLM processor
        
        Args:
            api_key: OpenRouter API key
            base_url: OpenRouter base URL
            model: LLM model to use
        """
        if AsyncOpenAI is None:
            raise ImportError("openai package is required for LLM processing. Install with: pip install openai")
        
        if not api_key:
            logger.warning("No OpenRouter API key provided. LLM processing will be disabled.")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url
            )
        
        self.model = model
    
    async def analyze_wikivoyage_content(
        self,
        country_name: str,
        raw_content: str,
        sections: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Analyze Wikivoyage content and extract structured information
        
        Args:
            country_name: Name of the country
            raw_content: Raw text content from Wikivoyage
            sections: Dictionary of section names and their content
            
        Returns:
            Structured dictionary with analyzed information
        """
        if not self.client:
            logger.warning("LLM client not available. Returning raw data.")
            return {
                "name": country_name,
                "raw_content": raw_content,
                "sections": sections
            }
        
        # Build prompt for LLM analysis
        prompt = self._build_analysis_prompt(country_name, raw_content, sections)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert travel data analyst. Extract structured information from travel guide content."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent extraction
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            logger.info(f"Successfully analyzed content for {country_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing content with LLM: {e}", exc_info=True)
            # Return fallback structure
            return {
                "name": country_name,
                "raw_content": raw_content,
                "sections": sections,
                "error": str(e)
            }
    
    def _build_analysis_prompt(
        self,
        country_name: str,
        raw_content: str,
        sections: Dict[str, str]
    ) -> str:
        """Build prompt for LLM analysis"""
        
        sections_text = "\n\n".join([
            f"## {section_name}\n{content}"
            for section_name, content in sections.items()
        ])
        
        prompt = f"""Analyze the following travel guide content for {country_name} and extract structured information.

RAW CONTENT:
{raw_content[:2000]}...

STRUCTURED SECTIONS:
{sections_text[:2000]}...

Extract and structure the following information in JSON format:

{{
  "country_name": "{country_name}",
  "summary": "Brief 2-3 sentence summary of the destination",
  "key_highlights": ["highlight1", "highlight2", ...],
  "practical_info": {{
    "visa_requirements": "...",
    "currency": "...",
    "language": "...",
    "time_zone": "...",
    "best_time_to_visit": "..."
  }},
  "transportation": {{
    "getting_in": ["method1", "method2", ...],
    "getting_around": ["method1", "method2", ...]
  }},
  "attractions": [
    {{
      "name": "...",
      "description": "...",
      "location": "...",
      "category": "museum|nature|historical|cultural|entertainment",
      "best_time_to_visit": "...",
      "tips": ["tip1", "tip2", ...]
    }}
  ],
  "accommodation": {{
    "types_available": ["hotel", "hostel", "apartment", ...],
    "price_range": "budget|mid-range|luxury",
    "recommended_areas": ["area1", "area2", ...]
  }},
  "dining": {{
    "cuisine_types": ["type1", "type2", ...],
    "price_range": "budget|mid-range|luxury",
    "specialties": ["dish1", "dish2", ...]
  }},
  "safety": {{
    "general_safety": "safe|moderate|caution_required",
    "warnings": ["warning1", "warning2", ...],
    "tips": ["tip1", "tip2", ...]
  }},
  "culture": {{
    "customs": ["custom1", "custom2", ...],
    "etiquette": ["rule1", "rule2", ...],
    "festivals": ["festival1", "festival2", ...]
  }},
  "budget": {{
    "daily_budget_low": "...",
    "daily_budget_mid": "...",
    "daily_budget_high": "...",
    "currency": "..."
  }}
}}

Focus on extracting practical, actionable information that would be useful for travelers. 
If information is not available in the content, use null or empty arrays.
Return ONLY valid JSON, no additional text."""
        
        return prompt
    
    async def enhance_attractions(
        self,
        attractions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enhance attraction data with LLM analysis
        
        Args:
            attractions: List of attraction dictionaries
            
        Returns:
            Enhanced list of attractions
        """
        if not self.client or not attractions:
            return attractions
        
        enhanced = []
        
        for attraction in attractions:
            try:
                # Build prompt for single attraction
                prompt = f"""Analyze and enhance the following attraction information:

{json.dumps(attraction, ensure_ascii=False, indent=2)}

Extract and structure the information in JSON format:

{{
  "name": "Full name of the attraction",
  "description": "Detailed 2-3 sentence description",
  "location": "Specific location/address",
  "category": "museum|nature|historical|cultural|entertainment|religious|outdoor",
  "highlights": ["key feature 1", "key feature 2", ...],
  "best_time_to_visit": "Best time of day/year to visit",
  "duration": "Recommended visit duration (e.g., '2-3 hours')",
  "price_info": "Entry fee information or 'free'",
  "tips": ["practical tip 1", "practical tip 2", ...],
  "nearby_attractions": ["attraction1", "attraction2", ...],
  "accessibility": "Information about accessibility",
  "opening_hours": "Opening hours if available"
}}

Return ONLY valid JSON, no additional text."""
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert travel guide analyzer. Extract structured information about tourist attractions."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                enhanced_attraction = json.loads(response.choices[0].message.content)
                # Merge with original data
                enhanced_attraction.update(attraction)
                enhanced.append(enhanced_attraction)
                
            except Exception as e:
                logger.warning(f"Error enhancing attraction {attraction.get('name', 'unknown')}: {e}")
                enhanced.append(attraction)  # Return original if enhancement fails
        
        return enhanced


"""
Skrypt do pobrania pełnej treści z Wikivoyage API i przetworzenia danych o Polsce
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from process_poland_html import parse_wikivoyage_html, update_country_json


async def fetch_full_wikivoyage_content(country_name: str = "Poland") -> str:
    """Pobiera pełną treść HTML z Wikivoyage API"""
    base_url = "https://en.wikivoyage.org/api/rest_v1"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Pobierz pełną treść HTML
        url = f"{base_url}/page/html/{country_name}"
        print(f"Pobieranie treści z: {url}")
        
        response = await client.get(url)
        response.raise_for_status()
        
        return response.text


async def main():
    """Główna funkcja"""
    print("=" * 60)
    print("Pobieranie i przetwarzanie danych o Polsce z Wikivoyage")
    print("=" * 60)
    
    try:
        # Pobierz pełną treść z API
        html_content = await fetch_full_wikivoyage_content("Poland")
        
        # Parsuj HTML
        print("\nParsowanie HTML...")
        country_data = parse_wikivoyage_html(html_content)
        
        # Wyświetl wyciągnięte dane
        print("\n" + "=" * 60)
        print("Wyciągnięte dane:")
        print("=" * 60)
        print(f"  Opis: {country_data['description'][:150]}...")
        print(f"  Historia: {'Tak (' + str(len(country_data['history'].split('\\n\\n')) if country_data['history'] else 0) + ' sekcji)' if country_data['history'] else 'Nie'}")
        print(f"  Języki: {', '.join(country_data['languages'])}")
        print(f"  Regiony: {len(country_data['metadata']['regions'])}")
        print(f"  Miasta: {len(country_data['metadata']['cities'])}")
        print(f"  Inne destynacje: {len(country_data['metadata']['other_destinations'])}")
        if country_data['coordinates']:
            print(f"  Współrzędne: lat={country_data['coordinates']['lat']}, lon={country_data['coordinates']['lon']}")
        print(f"  Informacje praktyczne: {'Tak' if country_data['practical_info'] else 'Nie'}")
        
        # Wyświetl informacje o sekcjach
        sections = country_data['metadata'].get('sections', {})
        print(f"\n  Wyciągnięte sekcje ({len(sections)}):")
        for section_name in sorted(sections.keys()):
            content_length = len(sections[section_name])
            print(f"    - {section_name}: {content_length} znaków")
        
        # Aktualizuj plik JSON
        output_dir = Path("data_ingestion_output")
        source = country_data.get("source", "wikivoyage_en")
        country_name = country_data.get("name", "Poland")
        print(f"\nAktualizowanie pliku dla źródła: {source}")
        update_country_json(output_dir, source, country_name, country_data)
        
        print("\n" + "=" * 60)
        print("✓ Zakończono pomyślnie!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Błąd: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)


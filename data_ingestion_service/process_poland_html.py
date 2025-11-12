"""
Skrypt do przetworzenia HTML Wikivoyage o Polsce i aktualizacji plików JSON
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from utils.file_manager import get_output_file_path


def parse_wikivoyage_html(html_content: str) -> Dict[str, Any]:
    """Parsuje HTML Wikivoyage i wyciąga dane o Polsce"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Wyciągnij współrzędne z JavaScript
    coordinates = None
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'wgCoordinates' in script.string:
            match = re.search(r'"wgCoordinates":\{"lat":([\d.]+),"lon":([\d.]+)\}', script.string)
            if match:
                coordinates = {
                    "lat": float(match.group(1)),
                    "lon": float(match.group(2))
                }
                break
    
    # Znajdź główną treść
    main_content = soup.find("div", class_="mw-parser-output")
    if not main_content:
        # Jeśli nie ma mw-parser-output, spróbuj znaleźć body content
        main_content = soup.find("body")
        if not main_content:
            main_content = soup
    
    def extract_section(heading_text: str) -> str:
        """Wyciąga zawartość sekcji"""
        if not main_content:
            return ""
        
        # Znajdź nagłówek
        heading = None
        for h in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = h.get_text().strip()
            if heading_text.lower() in text.lower():
                heading = h
                break
        
        if not heading:
            return ""
        
        # Zbierz zawartość
        content_parts = []
        current = heading.next_sibling
        heading_level = int(heading.name[1]) if heading.name and heading.name.startswith('h') else 2
        
        while current:
            if current.name and current.name.startswith('h'):
                level = int(current.name[1])
                if level <= heading_level:
                    break
            
            if current.name == 'p':
                text = current.get_text().strip()
                if text:
                    content_parts.append(text)
            elif current.name == 'ul':
                for li in current.find_all('li', recursive=False):
                    text = li.get_text().strip()
                    if text:
                        content_parts.append(f"• {text}")
            elif current.name == 'dl':
                for dt in current.find_all('dt', recursive=False):
                    term = dt.get_text().strip()
                    dd = dt.find_next_sibling('dd')
                    if dd:
                        definition = dd.get_text().strip()
                        content_parts.append(f"{term}: {definition}")
            
            current = current.next_sibling
        
        return "\n".join(content_parts)
    
    def extract_list_section(heading_text: str) -> List[str]:
        """Wyciąga elementy listy z sekcji"""
        if not main_content:
            return []
        
        heading = None
        for h in main_content.find_all(['h1', 'h2', 'h3', 'h4']):
            text = h.get_text().strip()
            if heading_text.lower() in text.lower():
                heading = h
                break
        
        if not heading:
            return []
        
        items = []
        current = heading.next_sibling
        heading_level = int(heading.name[1]) if heading.name and heading.name.startswith('h') else 2
        
        while current:
            if current.name and current.name.startswith('h'):
                level = int(current.name[1])
                if level <= heading_level:
                    break
            
            if current.name == 'ul':
                for li in current.find_all('li', recursive=False):
                    text = li.get_text().strip()
                    # Usuń nawiasy z linkami
                    text = re.sub(r'\s*\([^)]*\)\s*$', '', text)
                    # Usuń linki Wikivoyage
                    text = re.sub(r'\[.*?\]', '', text)
                    if text:
                        items.append(text)
            
            current = current.next_sibling
        
        return items
    
    # Wyciągnij podstawowe informacje
    description = ""
    understand_section = extract_section("Understand")
    if understand_section:
        # Pierwszy akapit jako opis
        lines = understand_section.split('\n')
        description = lines[0] if lines else ""
    
    # Wyciągnij historię
    history_sections = {}
    history_heading = None
    for h in main_content.find_all(['h2', 'h3', 'h4']):
        if h.get_text().strip().lower() == 'history':
            history_heading = h
            break
    
    if history_heading:
        current = history_heading.next_sibling
        history_level = int(history_heading.name[1])
        current_subsection = None
        current_content = []
        
        while current:
            if current.name and current.name.startswith('h'):
                level = int(current.name[1])
                if level > history_level:
                    if current_subsection and current_content:
                        history_sections[current_subsection] = "\n".join(current_content)
                    current_subsection = current.get_text().strip()
                    current_content = []
                elif level <= history_level:
                    if current_subsection and current_content:
                        history_sections[current_subsection] = "\n".join(current_content)
                    break
            elif current.name == 'p' and current_subsection:
                text = current.get_text().strip()
                if text:
                    current_content.append(text)
            elif current.name == 'ul' and current_subsection:
                for li in current.find_all('li', recursive=False):
                    text = li.get_text().strip()
                    if text:
                        current_content.append(f"• {text}")
            
            current = current.next_sibling
        
        if current_subsection and current_content:
            history_sections[current_subsection] = "\n".join(current_content)
    
    history_text = ""
    if history_sections:
        history_parts = []
        for section_name, section_content in history_sections.items():
            history_parts.append(f"{section_name}:\n{section_content}")
        history_text = "\n\n".join(history_parts)
    
    # Wyciągnij języki
    languages = []
    talk_section = extract_section("Talk")
    if talk_section:
        if 'polish' in talk_section.lower():
            languages.append("Polish")
        if 'english' in talk_section.lower():
            languages.append("English")
    
    if not languages:
        languages = ["Polish"]  # Domyślnie
    
    # Wyciągnij informacje praktyczne
    practical_info = extract_section("Get in")
    
    # Wyciągnij listy
    regions = extract_list_section("Regions")
    cities = extract_list_section("Cities")
    other_destinations = extract_list_section("Other destinations")
    
    # Wyciągnij wszystkie sekcje Wikivoyage
    all_section_names = [
        "Beginning", "Regions", "Cities", "Other destinations",
        "Understand", "Talk", "Get in", "Get around",
        "See", "Do", "Buy", "Eat", "Drink", "Sleep",
        "Learn", "Work", "Stay safe", "Stay healthy",
        "Respect", "Connect"
    ]
    
    all_sections = {}
    for section_name in all_section_names:
        content = extract_section(section_name)
        if content:
            all_sections[section_name.lower().replace(" ", "_")] = content
    
    # Rozszerz informacje praktyczne o Get around
    get_around_content = all_sections.get("get_around", "")
    if get_around_content and practical_info:
        practical_info = f"{practical_info}\n\nGet around:\n{get_around_content}"
    elif get_around_content:
        practical_info = f"Get around:\n{get_around_content}"
    
    # Zbuduj dane
    data = {
        "name": "Poland",
        "code": None,
        "capital": None,
        "population": None,
        "area_km2": None,
        "currency": None,
        "languages": languages,
        "timezone": None,
        "description": description or "Poland has a rich and eventful history, and a strong basis for its bourgeoning tourism industry. As one of Europe's most underrated countries, it offers a fair share of countryside, vibrant urbanity, pristine beauty and a culture in connection to its thousand-year history.",
        "history": history_text,
        "culture": "",
        "practical_info": practical_info,
        "coordinates": coordinates,
        "source": "wikivoyage_en",
        "source_url": "https://en.wikivoyage.org/wiki/Poland",
        "fetched_at": datetime.utcnow().isoformat(),
        "metadata": {
            "regions": regions,
            "cities": cities,
            "other_destinations": other_destinations,
            "sections": all_sections,
            # Dodatkowe strukturyzowane dane
            "attractions": {
                "see": all_sections.get("see", ""),
                "do": all_sections.get("do", ""),
            },
            "dining": {
                "eat": all_sections.get("eat", ""),
                "drink": all_sections.get("drink", ""),
            },
            "accommodation": {
                "sleep": all_sections.get("sleep", ""),
            },
            "shopping": {
                "buy": all_sections.get("buy", ""),
            },
            "practical": {
                "get_in": all_sections.get("get_in", ""),
                "get_around": all_sections.get("get_around", ""),
                "stay_safe": all_sections.get("stay_safe", ""),
                "stay_healthy": all_sections.get("stay_healthy", ""),
                "respect": all_sections.get("respect", ""),
                "connect": all_sections.get("connect", ""),
            },
            "other": {
                "learn": all_sections.get("learn", ""),
                "work": all_sections.get("work", ""),
            }
        }
    }
    
    return data


def update_country_json(
    output_dir: Path,
    source: str,
    country_name: str,
    new_data: Dict[str, Any]
):
    """
    Aktualizuje plik JSON z danymi o kraju w folderze źródła
    
    Args:
        output_dir: Główny katalog wyjściowy
        source: Nazwa źródła (np. 'wikivoyage_en')
        country_name: Nazwa kraju
        new_data: Nowe dane do zapisania
    """
    output_file = get_output_file_path(output_dir, source, country_name, "countries")
    
    # Wczytaj istniejące dane
    if output_file.exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    else:
        existing_data = []
    
    # Znajdź istniejący wpis z tym samym źródłem
    updated = False
    for i, item in enumerate(existing_data):
        if (item.get("name") == country_name and 
            item.get("source") == source):
            # Zaktualizuj istniejący wpis
            existing_data[i].update(new_data)
            updated = True
            break
    
    # Jeśli nie znaleziono, dodaj nowy wpis
    if not updated:
        existing_data.append(new_data)
    
    # Zapisz zaktualizowane dane
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"✓ Zaktualizowano plik: {output_file}")


def main():
    """Główna funkcja"""
    # Wczytaj HTML z pliku lub stdin
    if len(sys.argv) > 1:
        html_file = sys.argv[1]
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    else:
        # Wczytaj z stdin
        html_content = sys.stdin.read()
    
    # Parsuj HTML
    print("Parsowanie HTML Wikivoyage...")
    country_data = parse_wikivoyage_html(html_content)
    
    # Wyświetl wyciągnięte dane
    print("\nWyciągnięte dane:")
    print(f"  Opis: {country_data['description'][:100]}...")
    print(f"  Historia: {'Tak' if country_data['history'] else 'Nie'}")
    print(f"  Języki: {', '.join(country_data['languages'])}")
    print(f"  Regiony: {len(country_data['metadata']['regions'])}")
    print(f"  Miasta: {len(country_data['metadata']['cities'])}")
    print(f"  Inne destynacje: {len(country_data['metadata']['other_destinations'])}")
    print(f"  Współrzędne: {country_data['coordinates']}")
    
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
    update_country_json(output_dir, source, country_name, country_data)
    
    print("\n✓ Zakończono przetwarzanie!")


if __name__ == "__main__":
    main()


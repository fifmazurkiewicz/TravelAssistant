"""
Skrypt do parsowania HTML z Wikivoyage i wyciągania szczegółowych informacji o Polsce
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from utils.file_manager import get_output_file_path, save_data_to_source_file


class WikivoyageHTMLParser:
    """Parser do wyciągania danych z HTML Wikivoyage"""
    
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.main_content = self.soup.find("div", class_="mw-parser-output")
    
    def extract_coordinates(self) -> Optional[Dict[str, float]]:
        """Wyciąga współrzędne geograficzne z meta tagów lub skryptów"""
        # Szukaj w skryptach JavaScript
        scripts = self.soup.find_all('script')
        for script in scripts:
            if script.string and 'wgCoordinates' in script.string:
                match = re.search(r'"wgCoordinates":\{"lat":([\d.]+),"lon":([\d.]+)\}', script.string)
                if match:
                    return {
                        "lat": float(match.group(1)),
                        "lon": float(match.group(2))
                    }
        return None
    
    def extract_section_content(self, section_title: str) -> str:
        """Wyciąga zawartość sekcji po nagłówku"""
        if not self.main_content:
            return ""
        
        # Znajdź nagłówek sekcji
        heading = None
        for h in self.main_content.find_all(['h2', 'h3', 'h4']):
            heading_text = h.get_text().strip()
            if section_title.lower() in heading_text.lower():
                heading = h
                break
        
        if not heading:
            return ""
        
        # Zbierz zawartość do następnego nagłówka tego samego lub wyższego poziomu
        content_parts = []
        current = heading.next_sibling
        heading_level = int(heading.name[1]) if heading.name.startswith('h') else 2
        
        while current:
            if current.name and current.name.startswith('h'):
                current_level = int(current.name[1])
                if current_level <= heading_level:
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
                # Definicje (np. w sekcji Talk)
                for dt in current.find_all('dt', recursive=False):
                    term = dt.get_text().strip()
                    dd = dt.find_next_sibling('dd')
                    if dd:
                        definition = dd.get_text().strip()
                        content_parts.append(f"{term}: {definition}")
            
            current = current.next_sibling
        
        return "\n".join(content_parts)
    
    def extract_list_items(self, section_title: str) -> List[str]:
        """Wyciąga elementy listy z sekcji"""
        if not self.main_content:
            return []
        
        heading = None
        for h in self.main_content.find_all(['h2', 'h3', 'h4']):
            heading_text = h.get_text().strip()
            if section_title.lower() in heading_text.lower():
                heading = h
                break
        
        if not heading:
            return []
        
        items = []
        current = heading.next_sibling
        heading_level = int(heading.name[1]) if heading.name.startswith('h') else 2
        
        while current:
            if current.name and current.name.startswith('h'):
                current_level = int(current.name[1])
                if current_level <= heading_level:
                    break
            
            if current.name == 'ul':
                for li in current.find_all('li', recursive=False):
                    text = li.get_text().strip()
                    # Usuń nawiasy z linkami Wikivoyage
                    text = re.sub(r'\s*\([^)]*\)\s*$', '', text)
                    if text:
                        items.append(text)
            
            current = current.next_sibling
        
        return items
    
    def extract_history_sections(self) -> Dict[str, str]:
        """Wyciąga sekcje historii"""
        history_sections = {}
        
        # Znajdź sekcję History
        history_heading = None
        for h in self.main_content.find_all(['h2', 'h3']):
            if h.get_text().strip().lower() == 'history':
                history_heading = h
                break
        
        if not history_heading:
            return history_sections
        
        # Znajdź podsekcje historii
        current = history_heading.next_sibling
        history_level = int(history_heading.name[1])
        current_subsection = None
        current_content = []
        
        while current:
            if current.name and current.name.startswith('h'):
                level = int(current.name[1])
                
                # Jeśli znaleźliśmy nową podsekcję
                if level > history_level:
                    if current_subsection and current_content:
                        history_sections[current_subsection] = "\n".join(current_content)
                    current_subsection = current.get_text().strip()
                    current_content = []
                # Jeśli znaleźliśmy nową sekcję główną, zakończ
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
        
        # Dodaj ostatnią sekcję
        if current_subsection and current_content:
            history_sections[current_subsection] = "\n".join(current_content)
        
        return history_sections
    
    def extract_languages(self) -> List[str]:
        """Wyciąga informacje o językach z sekcji Talk"""
        talk_content = self.extract_section_content("Talk")
        languages = []
        
        # Szukaj wzorców językowych
        # Przykład: "Polish is the official language..."
        polish_match = re.search(r'[Pp]olish', talk_content)
        if polish_match:
            languages.append("Polish")
        
        # Szukaj innych języków
        language_patterns = [
            r'([A-Z][a-z]+)\s+is\s+(?:the\s+)?(?:official\s+)?language',
            r'languages?:\s*([A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+)*)',
        ]
        
        for pattern in language_patterns:
            matches = re.findall(pattern, talk_content)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                langs = [l.strip() for l in match.split(',')]
                languages.extend(langs)
        
        # Usuń duplikaty i posortuj
        languages = sorted(list(set(languages)))
        
        return languages if languages else []
    
    def extract_all_sections(self) -> Dict[str, Any]:
        """Wyciąga wszystkie sekcje z przewodnika Wikivoyage"""
        sections = {}
        
        # Lista wszystkich sekcji do wyciągnięcia
        section_names = [
            "Beginning",
            "Regions",
            "Cities",
            "Other destinations",
            "Understand",
            "Talk",
            "Get in",
            "Get around",
            "See",
            "Do",
            "Buy",
            "Eat",
            "Drink",
            "Sleep",
            "Learn",
            "Work",
            "Stay safe",
            "Stay healthy",
            "Respect",
            "Connect"
        ]
        
        for section_name in section_names:
            content = self.extract_section_content(section_name)
            if content:
                sections[section_name.lower().replace(" ", "_")] = content
        
        return sections
    
    def parse_country_data(self) -> Dict[str, Any]:
        """Główna metoda parsująca dane o kraju"""
        # Wyciągnij wszystkie sekcje
        all_sections = self.extract_all_sections()
        
        # Wyciągnij podstawowy opis z Understand
        understand_content = all_sections.get("understand", "")
        description = understand_content.split('\n')[0] if understand_content else ""
        
        data = {
            "name": "Poland",
            "description": description,
            "history": "",
            "practical_info": "",
            "coordinates": self.extract_coordinates(),
            "source": "wikivoyage_en",
            "source_url": "https://en.wikivoyage.org/wiki/Poland",
            "fetched_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
        
        # Wyciągnij historię z sekcji Understand
        history_sections = self.extract_history_sections()
        if history_sections:
            history_text = []
            for section_name, section_content in history_sections.items():
                history_text.append(f"{section_name}:\n{section_content}")
            data["history"] = "\n\n".join(history_text)
        
        # Wyciągnij języki
        languages = self.extract_languages()
        if languages:
            data["languages"] = languages
        else:
            data["languages"] = ["Polish"]  # Domyślnie polski
        
        # Wyciągnij informacje praktyczne (Get in + Get around)
        get_in_content = all_sections.get("get_in", "")
        get_around_content = all_sections.get("get_around", "")
        practical_parts = []
        if get_in_content:
            practical_parts.append(f"Get in:\n{get_in_content}")
        if get_around_content:
            practical_parts.append(f"Get around:\n{get_around_content}")
        if practical_parts:
            data["practical_info"] = "\n\n".join(practical_parts)
        
        # Dodaj regiony, miasta i inne destynacje do metadanych
        regions = self.extract_list_items("Regions")
        cities = self.extract_list_items("Cities")
        other_destinations = self.extract_list_items("Other destinations")
        
        # Dodaj wszystkie sekcje do metadanych
        data["metadata"] = {
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
        
        return data


def parse_html_file(html_file_path: str) -> Dict[str, Any]:
    """Parsuje plik HTML i zwraca dane o kraju"""
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    parser = WikivoyageHTMLParser(html_content)
    return parser.parse_country_data()


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


if __name__ == "__main__":
    # Przykład użycia - jeśli masz plik HTML
    # html_file = "poland_wikivoyage.html"
    # country_data = parse_html_file(html_file)
    # update_country_json("data_ingestion_output/poland_countries.json", country_data)
    
    print("Skrypt do parsowania HTML Wikivoyage")
    print("Użyj funkcji parse_html_file() z zawartością HTML")


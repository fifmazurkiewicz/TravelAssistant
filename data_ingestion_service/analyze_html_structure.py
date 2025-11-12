"""
Skrypt do analizy struktury HTML z Wikivoyage
"""
from pathlib import Path
from bs4 import BeautifulSoup


def analyze_html_structure(html_file: str):
    """Analizuje strukturę HTML i wyciąga sekcje"""
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    main_content = soup.find("div", class_="mw-parser-output")
    
    if not main_content:
        print(f"Nie znaleziono głównej treści w {html_file}")
        return
    
    # Znajdź wszystkie nagłówki
    headings = main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    print(f"\n{'='*80}")
    print(f"Analiza: {Path(html_file).name}")
    print(f"{'='*80}")
    print(f"\nZnaleziono {len(headings)} nagłówków:\n")
    
    sections = []
    for heading in headings:
        level = int(heading.name[1]) if heading.name.startswith('h') else 0
        text = heading.get_text().strip()
        heading_id = heading.get('id', '')
        
        # Znajdź span z id
        span = heading.find('span', class_='mw-headline')
        if span:
            heading_id = span.get('id', '')
        
        sections.append({
            'level': level,
            'text': text,
            'id': heading_id
        })
        
        indent = "  " * (level - 1)
        print(f"{indent}H{level}: {text} (id: {heading_id})")
    
    # Sprawdź czy są listy (Regions, Cities, etc.)
    print(f"\n{'='*80}")
    print("Listy (Regions, Cities, Other destinations):")
    print(f"{'='*80}\n")
    
    for heading in headings:
        text = heading.get_text().strip().lower()
        if any(keyword in text for keyword in ['regions', 'cities', 'other destinations', 'destinations']):
            print(f"\nSekcja: {heading.get_text().strip()}")
            # Znajdź listę po tym nagłówku
            current = heading.next_sibling
            while current:
                if current.name == 'ul':
                    items = current.find_all('li', recursive=False)
                    print(f"  Znaleziono {len(items)} elementów:")
                    for i, li in enumerate(items[:5], 1):  # Pokaż pierwsze 5
                        item_text = li.get_text().strip()
                        print(f"    {i}. {item_text[:80]}...")
                    if len(items) > 5:
                        print(f"    ... i {len(items) - 5} więcej")
                    break
                if current.name and current.name.startswith('h'):
                    break
                current = current.next_sibling
    
    return sections


def compare_html_files(file1: str, file2: str):
    """Porównuje strukturę dwóch plików HTML"""
    print("\n" + "="*80)
    print("PORÓWNANIE PLIKÓW HTML")
    print("="*80)
    
    sections1 = analyze_html_structure(file1)
    sections2 = analyze_html_structure(file2)
    
    if not sections1 or not sections2:
        return
    
    # Porównaj sekcje
    print(f"\n{'='*80}")
    print("PORÓWNANIE SEKCJI:")
    print(f"{'='*80}\n")
    
    texts1 = {s['text'].lower() for s in sections1}
    texts2 = {s['text'].lower() for s in sections2}
    
    common = texts1 & texts2
    only_in_1 = texts1 - texts2
    only_in_2 = texts2 - texts1
    
    print(f"Wspólne sekcje ({len(common)}):")
    for sec in sorted(common):
        print(f"  ✓ {sec}")
    
    if only_in_1:
        print(f"\nTylko w {Path(file1).name} ({len(only_in_1)}):")
        for sec in sorted(only_in_1):
            print(f"  → {sec}")
    
    if only_in_2:
        print(f"\nTylko w {Path(file2).name} ({len(only_in_2)}):")
        for sec in sorted(only_in_2):
            print(f"  → {sec}")
    
    # Sprawdź czy to te same strony
    print(f"\n{'='*80}")
    print("WNIOSEK:")
    print(f"{'='*80}\n")
    
    if len(common) == len(texts1) == len(texts2) and len(common) > 10:
        print("✓ Pliki mają IDENTYCZNĄ strukturę sekcji - to prawdopodobnie ta sama strona!")
    elif len(common) > len(only_in_1) + len(only_in_2):
        print("⚠ Pliki mają PODOBNĄ strukturę, ale różnią się niektórymi sekcjami")
    else:
        print("✗ Pliki mają RÓŻNĄ strukturę sekcji")


if __name__ == "__main__":
    file1 = "data_ingestion_output/wikivoyage/html/poland_countries.html"
    file2 = "data_ingestion_output/wikivoyage/html/poland_attractions_poland.html"
    
    compare_html_files(file1, file2)


import sys
import re
from lxml import etree
from typing import Tuple

# ANSI Farb-Codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

def calculate_isbn10_checksum(isbn: str) -> bool:
    """Berechnet und überprüft die Prüfsumme einer ISBN-10."""
    if len(isbn) != 10:
        return False
    
    try:
        # Umwandlung von 'X' in '10' für die letzte Stelle
        digits = [10 if x in 'Xx' else int(x) for x in isbn]
        # Prüfsummenberechnung: (11 - (sum(d[i] * (10-i)) mod 11)) mod 11
        checksum = sum((10 - i) * digit for i, digit in enumerate(digits)) % 11
        return checksum == 0
    except ValueError:
        return False

def calculate_isbn13_checksum(isbn: str) -> bool:
    """Berechnet und überprüft die Prüfsumme einer ISBN-13."""
    if len(isbn) != 13:
        return False
    
    try:
        digits = [int(x) for x in isbn]
        # Prüfsummenberechnung: sum(d[i] * (1 if i%2==0 else 3)) mod 10 should be 0
        checksum = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits)) % 10
        return checksum == 0
    except ValueError:
        return False

def validate_isbn(isbn: str) -> Tuple[bool, str]:
    """Validiert eine ISBN und gibt ein Tupel (is_valid, cleaned_isbn) zurück."""
    # Bereinigung der ISBN
    cleaned = re.sub(r'[-\s]', '', isbn)
    
    # Validierung basierend auf der Länge
    if len(cleaned) == 10:
        return calculate_isbn10_checksum(cleaned), cleaned
    elif len(cleaned) == 13:
        return calculate_isbn13_checksum(cleaned), cleaned
    return False, cleaned

def extract_isbns(text):
    # Erweitertes Regex-Muster für verschiedene ISBN-Formate
    isbn_pattern = r'ISBN(?:[-\s]1[03])?:?\s?((?:97[89][-\s]?)?(?:\d[-\s]?){9}[\dXx])'
    
    # Weitere spezifische Muster für Vorlagen
    template_patterns = [
        r'\{\{ISBNpur\|((?:\d{10}|\d{13}))\}\}',    # {{ISBNpur|1234567890}}
        r'\{\{BibISBN\|((?:\d{10}|\d{13}))\}\}',    # {{BibISBN|1234567890}}
    ]
    
    isbns = re.findall(isbn_pattern, text, re.IGNORECASE)
    
    for pattern in template_patterns:
        isbns.extend(re.findall(pattern, text, re.IGNORECASE))
    
    # Bereinigung und Validierung der gefundenen ISBNs
    validated_isbns = []
    for isbn in isbns:
        is_valid, cleaned = validate_isbn(isbn)
        if len(cleaned) in [10, 13]:  # Nur 10- oder 13-stellige ISBNs
            validated_isbns.append((cleaned, is_valid))
    
    return list(set(validated_isbns))  # Entfernt Duplikate

def parse_wikipedia_xml(file_path, invalid_only=False):
    context = etree.iterparse(file_path, events=('end',), tag='{http://www.mediawiki.org/xml/export-0.11/}page')
    
    for _, elem in context:
        ns = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}ns').text
        if ns == '0':  # Nur Artikel im Hauptnamensraum
            title = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}title').text
            page_id = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}id').text
            text_elem = elem.find('.//{http://www.mediawiki.org/xml/export-0.11/}text')
            
            if text_elem is not None and text_elem.text:
                validated_isbns = extract_isbns(text_elem.text)
                for isbn, is_valid in validated_isbns:
                    if not invalid_only or (invalid_only and not is_valid):
                        color = GREEN if is_valid else RED
                        print(f"{page_id}\t{title}\t{color}{isbn}{RESET}")
        
        elem.clear()
        for ancestor in elem.xpath('ancestor-or-self::*'):
            while ancestor.getprevious() is not None:
                del ancestor.getparent()[0]
    
    del context

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python script_name.py <path_to_xml_file> [--invalid-only]")
        sys.exit(1)
    
    invalid_only = len(sys.argv) == 3 and sys.argv[2] == "--invalid-only"
    parse_wikipedia_xml(sys.argv[1], invalid_only)

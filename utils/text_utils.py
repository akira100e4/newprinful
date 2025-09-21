# utils/text_utils.py - Versione estesa con slug generator OnlyOne
import re
import unicodedata
from typing import List, Optional

def slugify(text: str) -> str:
    """Converte il testo in slug per URL"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', '_', text)
    text = text.strip('_')
    return text

def normalize_product_name(filename: str) -> str:
    """Normalizza il nome del prodotto dal nome file"""
    # Rimuovi estensione
    if '.' in filename:
        filename = filename.rsplit('.', 1)[0]
    
    # Rimuovi suffissi colore comuni
    color_suffixes = ['_dark_gray', '_light_gray', '_black', '_white']
    for suffix in color_suffixes:
        if filename.endswith(suffix):
            filename = filename[:-len(suffix)]
    
    return filename

def is_light_color(color: str) -> bool:
    """Determina se un colore è chiaro"""
    from config_printful import LIGHT_COLORS
    return color in LIGHT_COLORS

def create_product_description(product_name: str) -> str:
    """Crea la descrizione del prodotto per Printful"""
    from config_printful import PRODUCT_DESCRIPTION_TEMPLATE
    return PRODUCT_DESCRIPTION_TEMPLATE.format(title=product_name)

def create_product_title(base_name: str, product_type: str) -> str:
    """Crea il titolo del prodotto"""
    type_names = {
        'tshirt': 'T-Shirt',
        'hoodie': 'Hoodie', 
        'sweatshirt': 'Sweatshirt',
        'cap': 'Cap'
    }
    
    product_type_name = type_names.get(product_type, product_type.title())
    from config_printful import PRODUCT_TITLE_TEMPLATE
    return PRODUCT_TITLE_TEMPLATE.format(title=f"{base_name} — {product_type_name}")

# ==================== ONLYONE SLUG GENERATOR ====================

def remove_accents(text: str) -> str:
    """Rimuove accenti e caratteri speciali Unicode"""
    # Normalizza Unicode (NFD = decompone caratteri accentati)
    nfd = unicodedata.normalize('NFD', text)
    # Filtra solo caratteri ASCII (rimuove accenti)
    ascii_text = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return ascii_text

def generate_kebab_slug(filename: str) -> str:
    """
    Genera slug in kebab-case da nome file
    
    "Il Cavallo Spettrale.png" → "cavallo-spettrale"
    "Farfalla Cosmica.jpg" → "farfalla-cosmica" 
    
    Args:
        filename: Nome file originale
        
    Returns:
        Slug kebab-case pulito
    """
    # Rimuovi estensione
    name = filename
    if '.' in name:
        name = name.rsplit('.', 1)[0]
    
    # Rimuovi accenti
    name = remove_accents(name)
    
    # Converti a lowercase
    name = name.lower()
    
    # Rimuovi articoli italiani comuni all'inizio
    articles = ['il ', 'la ', 'lo ', 'gli ', 'le ', 'un ', 'una ', 'uno ']
    for article in articles:
        if name.startswith(article):
            name = name[len(article):]
            break
    
    # Sostituisci spazi multipli con spazio singolo
    name = re.sub(r'\s+', ' ', name)
    
    # Rimuovi caratteri non alfanumerici (tieni solo lettere, numeri, spazi)
    name = re.sub(r'[^a-z0-9\s]', '', name)
    
    # Converti spazi in trattini
    slug = re.sub(r'\s+', '-', name.strip())
    
    # Rimuovi trattini multipli
    slug = re.sub(r'-+', '-', slug)
    
    # Rimuovi trattini all'inizio e fine
    slug = slug.strip('-')
    
    return slug

def extract_title_from_slug(slug: str, max_words: int = 4) -> str:
    """
    Estrae titolo presentabile da slug (max 3-4 parole)
    
    "cavallo-spettrale" → "Cavallo Spettrale"
    "guardiano-dell-obelisco" → "Guardiano dell'Obelisco"
    
    Args:
        slug: Slug kebab-case
        max_words: Numero massimo parole
        
    Returns:
        Titolo capitalizzato
    """
    # Sostituisci trattini con spazi
    title = slug.replace('-', ' ')
    
    # Split in parole
    words = title.split()
    
    # Limita numero parole
    if len(words) > max_words:
        words = words[:max_words]
    
    # Capitalizza ogni parola
    title_words = []
    for word in words:
        # Gestisci articoli/preposizioni italiane (lowercase)
        if word.lower() in ['del', 'della', 'dell', 'dello', 'dei', 'degli', 'delle', 
                           'di', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra', 'a', 'e']:
            if len(title_words) > 0:  # Non all'inizio
                title_words.append(word.lower())
            else:
                title_words.append(word.capitalize())
        else:
            title_words.append(word.capitalize())
    
    return ' '.join(title_words)

def validate_slug(slug: str) -> dict:
    """
    Valida slug generato
    
    Returns:
        Dict con risultato validazione
    """
    result = {
        'valid': True,
        'slug': slug,
        'issues': [],
        'warnings': []
    }
    
    # Controlla lunghezza
    if len(slug) < 3:
        result['valid'] = False
        result['issues'].append("Slug troppo corto (< 3 caratteri)")
    elif len(slug) > 50:
        result['warnings'].append("Slug lungo (> 50 caratteri)")
    
    # Controlla caratteri permessi
    if not re.match(r'^[a-z0-9-]+$', slug):
        result['valid'] = False
        result['issues'].append("Caratteri non permessi (solo a-z, 0-9, -)")
    
    # Controlla trattini consecutivi
    if '--' in slug:
        result['valid'] = False
        result['issues'].append("Trattini consecutivi non permessi")
    
    # Controlla inizio/fine con trattino
    if slug.startswith('-') or slug.endswith('-'):
        result['valid'] = False
        result['issues'].append("Non può iniziare/finire con trattino")
    
    return result

def generate_unique_slug(filename: str, existing_slugs: List[str]) -> str:
    """
    Genera slug unico evitando duplicati
    
    Args:
        filename: Nome file originale
        existing_slugs: Lista slug già esistenti
        
    Returns:
        Slug unico con suffisso numerico se necessario
    """
    base_slug = generate_kebab_slug(filename)
    
    if base_slug not in existing_slugs:
        return base_slug
    
    # Genera versioni con suffisso numerico
    counter = 2
    while f"{base_slug}-{counter}" in existing_slugs:
        counter += 1
    
    return f"{base_slug}-{counter}"

def batch_generate_slugs(filenames: List[str]) -> dict:
    """
    Genera slug per lista di file evitando duplicati
    
    Args:
        filenames: Lista nomi file
        
    Returns:
        Dict {filename: slug} con mapping e statistiche
    """
    result = {
        'mappings': {},
        'duplicates_found': [],
        'invalid_slugs': [],
        'stats': {
            'total': len(filenames),
            'valid': 0,
            'duplicates': 0,
            'invalid': 0
        }
    }
    
    existing_slugs = []
    
    for filename in filenames:
        # Genera slug unico
        slug = generate_unique_slug(filename, existing_slugs)
        
        # Valida slug
        validation = validate_slug(slug)
        
        if validation['valid']:
            result['mappings'][filename] = slug
            existing_slugs.append(slug)
            result['stats']['valid'] += 1
            
            # Controlla se era duplicato
            base_slug = generate_kebab_slug(filename)
            if slug != base_slug:
                result['duplicates_found'].append({
                    'filename': filename,
                    'base_slug': base_slug,
                    'unique_slug': slug
                })
                result['stats']['duplicates'] += 1
        else:
            result['invalid_slugs'].append({
                'filename': filename,
                'issues': validation['issues']
            })
            result['stats']['invalid'] += 1
    
    return result

def format_title_for_display(title: str) -> str:
    """
    Formatta titolo per display pubblico (rimuove punteggiatura superflua)
    
    Args:
        title: Titolo grezzo
        
    Returns:
        Titolo pulito per display
    """
    # Rimuovi punteggiatura finale superflua
    title = title.rstrip('.,;:!?')
    
    # Gestisci apostrofi speciali
    title = title.replace("'", "'")  # Apostrofo tipografico
    title = re.sub(r"\s+'", "'", title)  # Rimuovi spazi prima apostrofo
    
    # Pulisci spazi multipli
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title
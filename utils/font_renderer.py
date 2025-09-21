# utils/font_renderer.py - Font renderer adattato per OnlyOne workflow
from PIL import Image, ImageDraw, ImageFont
import math
import os
import re
import json
import glob
from typing import Dict, Tuple, Optional, List

def draw_curved_text(text: str, font_path: str, font_size: int, 
                    image_size: Tuple[int, int] = (2400, 800), 
                    curve_strength: float = -0.60, 
                    color: Tuple[int, int, int, int] = (0, 0, 0, 255)) -> Image.Image:
    """
    Disegna testo curvato con Libre Bodoni.
    Adattato per OnlyOne workflow con curvatura configurabile.
    
    Args:
        text: Testo da renderizzare
        font_path: Path del font Libre Bodoni
        font_size: Dimensione font in pixel
        image_size: Dimensioni canvas (width, height)
        curve_strength: Intensità curvatura (negativo=curva verso basso)
        color: Colore RGBA
        
    Returns:
        PIL Image con testo curvato e sfondo trasparente
    """
    w, h = image_size
    center_x = w // 2
    center_y = h // 2 + 50  # Compensazione verticale 

    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        print(f"❌ Errore caricamento font {font_path}: {e}")
        # Fallback a font di sistema
        font = ImageFont.load_default()

    # Calcola la larghezza totale del testo
    text_width = sum(font.getbbox(char)[2] for char in text)
    radius = text_width / (2 * math.pi * abs(curve_strength) if abs(curve_strength) > 0 else 0.01)

    current_x = -text_width / 2

    img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    for char in text:
        char_width = font.getbbox(char)[2]
        angle = (current_x + char_width / 2) / radius

        x = center_x + radius * math.sin(angle)
        y = center_y + (radius * (1 - math.cos(angle))) * (-1 if curve_strength < 0 else 1)

        # Crea immagine singola della lettera
        char_img = Image.new("RGBA", (font_size * 2, font_size * 2), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_img)
        char_draw.text((font_size, font_size), char, font=font, fill=color, anchor="mm")

        # Ruota e compone
        rotated = char_img.rotate(math.degrees(angle), resample=Image.Resampling.BICUBIC, center=(font_size, font_size))
        img.alpha_composite(rotated, (int(x - font_size), int(y - font_size)))

        current_x += char_width

    return img

def render_title_with_libre_bodoni(title: str, output_dir: str = "artifacts") -> Dict[str, str]:
    """
    Genera titolo con Libre Bodoni in versioni light e dark.
    Integrato con configurazione OnlyOne.
    
    Args:
        title: Titolo da renderizzare (es. "Cavallo Spettrale")
        output_dir: Directory output per i file generati
        
    Returns:
        Dict con path dei file generati: {'dark': path, 'light': path}
    """
    from config_printful import LIBRE_BODONI_FONT, CONTRAST_COLORS
    from utils.text_utils import generate_kebab_slug
    
    # Configurazione da config
    font_path = LIBRE_BODONI_FONT['regular']
    font_size = 180  # Dimensione base
    curve_strength = LIBRE_BODONI_FONT.get('curve', -0.11)
    
    # Colori esatti OnlyOne
    dark_color = tuple(int(CONTRAST_COLORS['dark_text'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (255,)  # #111111
    light_color = tuple(int(CONTRAST_COLORS['light_text'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (255,) # #FFFFFF
    
    # Genera slug per nomi file
    slug = generate_kebab_slug(title)
    
    # Crea directory output
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🎨 Rendering titolo: '{title}' (slug: {slug})")
    
    try:
        # Verifica font esistente
        if not os.path.exists(font_path):
            print(f"⚠️ Font non trovato: {font_path}")
            print(f"   Cerca in: {os.path.join('assets', 'fonts', 'Libre_Bodoni', 'static', 'LibreBodoni-Regular.ttf')}")
            return {'dark': None, 'light': None}
        
        # Genera immagini
        img_dark = draw_curved_text(title, font_path, font_size, color=dark_color, curve_strength=curve_strength)
        img_light = draw_curved_text(title, font_path, font_size, color=light_color, curve_strength=curve_strength)
        
        # Path output
        dark_path = os.path.join(output_dir, f"{slug}_title_dark.png")
        light_path = os.path.join(output_dir, f"{slug}_title_light.png")
        
        # Salvataggio
        img_dark.save(dark_path, "PNG", optimize=True)
        img_light.save(light_path, "PNG", optimize=True)
        
        print(f"  ✅ Dark: {os.path.basename(dark_path)}")
        print(f"  ✅ Light: {os.path.basename(light_path)}")
        
        return {
            'dark': dark_path,
            'light': light_path,
            'title': title,
            'slug': slug
        }
        
    except Exception as e:
        print(f"❌ Errore rendering titolo '{title}': {e}")
        return {'dark': None, 'light': None}

def load_metadata_from_json(metadata_dir: str = "fase1/output/generated_metadati") -> Dict[str, str]:
    """
    Carica i metadati dai file JSON (compatibilità con sistema esistente).
    
    Args:
        metadata_dir: Directory contenente i file JSON dei metadati
        
    Returns:
        Dict con mapping filename_slug -> original_title
    """
    metadata_mapping = {}
    
    if not os.path.exists(metadata_dir):
        print(f"⚠️ Directory metadati non trovata: {metadata_dir}")
        return metadata_mapping
    
    # Trova tutti i file JSON nella directory
    json_files = glob.glob(os.path.join(metadata_dir, "*.json"))
    
    print(f"📄 Trovati {len(json_files)} file JSON di metadati")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Estrai il titolo originale dal JSON
            original_title = data.get('title', data.get('name', ''))
            
            if original_title:
                # Usa il nome del file JSON come chiave
                json_filename = os.path.splitext(os.path.basename(json_file))[0]
                
                # Genera slug compatibile OnlyOne
                from utils.text_utils import generate_kebab_slug
                slug_key = generate_kebab_slug(json_filename)
                
                metadata_mapping[slug_key] = original_title
                print(f"  ✅ {slug_key} -> {original_title}")
            else:
                print(f"  ⚠️ Titolo non trovato in {json_file}")
                
        except Exception as e:
            print(f"  ❌ Errore nel caricare {json_file}: {e}")
    
    return metadata_mapping

def extract_title_from_filename(filename: str, metadata_mapping: Optional[Dict[str, str]] = None) -> str:
    """
    Estrae titolo da nome file, usando metadati se disponibili.
    
    Args:
        filename: Nome file (es. "il-cavallo-spettrale.png")
        metadata_mapping: Mapping metadati opzionale
        
    Returns:
        Titolo formattato per display
    """
    from utils.text_utils import generate_kebab_slug, extract_title_from_slug
    
    # Rimuovi estensione
    base_name = os.path.splitext(os.path.basename(filename))[0]
    
    # Genera slug
    slug = generate_kebab_slug(base_name)
    
    # Cerca nei metadati se disponibili
    if metadata_mapping and slug in metadata_mapping:
        title = metadata_mapping[slug]
        print(f"📖 Titolo da metadati: '{title}'")
        return title
    
    # Fallback: estrai da slug
    title = extract_title_from_slug(slug)
    print(f"📝 Titolo da slug: '{title}'")
    return title

def batch_generate_titles_for_images(image_files: List[str], 
                                    output_dir: str = "artifacts",
                                    metadata_dir: Optional[str] = None) -> Dict[str, Dict]:
    """
    Genera titoli per lista di immagini.
    Integrato con workflow OnlyOne.
    
    Args:
        image_files: Lista path immagini
        output_dir: Directory output
        metadata_dir: Directory metadati JSON (opzionale)
        
    Returns:
        Dict con risultati generazione per ogni file
    """
    results = {}
    
    # Carica metadati se disponibili
    metadata_mapping = {}
    if metadata_dir and os.path.exists(metadata_dir):
        metadata_mapping = load_metadata_from_json(metadata_dir)
    
    print(f"\n🎨 GENERAZIONE TITOLI PER {len(image_files)} IMMAGINI")
    print("="*50)
    
    for image_file in image_files:
        filename = os.path.basename(image_file)
        print(f"\n📁 Processando: {filename}")
        
        try:
            # Estrai titolo da file/metadati
            title = extract_title_from_filename(filename, metadata_mapping)
            
            # Genera titoli
            result = render_title_with_libre_bodoni(title, output_dir)
            
            results[image_file] = {
                'success': result['dark'] is not None and result['light'] is not None,
                'title': title,
                'slug': result.get('slug'),
                'dark_path': result.get('dark'),
                'light_path': result.get('light')
            }
            
        except Exception as e:
            print(f"❌ Errore processando {filename}: {e}")
            results[image_file] = {
                'success': False,
                'error': str(e)
            }
    
    # Summary
    successful = sum(1 for r in results.values() if r.get('success'))
    print(f"\n📊 RISULTATI: {successful}/{len(image_files)} titoli generati")
    
    return results

def get_title_file_paths(product_slug: str, output_dir: str = "artifacts") -> Tuple[str, str]:
    """
    Genera path dei file titolo per slug prodotto.
    Compatibile con naming OnlyOne.
    
    Args:
        product_slug: Slug prodotto (es. "cavallo-spettrale")
        output_dir: Directory titoli
        
    Returns:
        Tuple (dark_path, light_path)
    """
    dark_path = os.path.join(output_dir, f"{product_slug}_title_dark.png")
    light_path = os.path.join(output_dir, f"{product_slug}_title_light.png")
    
    return dark_path, light_path

def verify_title_files_exist(product_slug: str, output_dir: str = "artifacts") -> Dict[str, bool]:
    """
    Verifica esistenza file titolo per prodotto.
    
    Args:
        product_slug: Slug prodotto
        output_dir: Directory titoli
        
    Returns:
        Dict con status esistenza file
    """
    dark_path, light_path = get_title_file_paths(product_slug, output_dir)
    
    return {
        'dark_exists': os.path.exists(dark_path),
        'light_exists': os.path.exists(light_path),
        'dark_path': dark_path,
        'light_path': light_path,
        'both_exist': os.path.exists(dark_path) and os.path.exists(light_path)
    }

# Funzione legacy per compatibilità con codice esistente
def process_image_with_title(image_path: str, metadata_mapping: Dict[str, str], 
                           output_dir: str = "Titoli") -> Tuple[Optional[str], Optional[str]]:
    """
    Compatibilità con codice esistente.
    Wrapper per la nuova funzione render_title_with_libre_bodoni.
    """
    filename = os.path.basename(image_path)
    title = extract_title_from_filename(filename, metadata_mapping)
    
    result = render_title_with_libre_bodoni(title, output_dir)
    
    return result.get('dark'), result.get('light')
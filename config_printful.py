# config_printful.py - Versione estesa per OnlyOne workflow
import os
from dotenv import load_dotenv

# Carica le variabili d'ambiente
load_dotenv()

# API Configuration
PRINTFUL_API_KEY = os.getenv('PRINTFUL_API_KEY')
PRINTFUL_STORE_ID = os.getenv('PRINTFUL_STORE_ID')

# API Base URL
PRINTFUL_API_BASE = "https://api.printful.com"

# Product IDs Printful (equivalenti ai Blueprint di Printify)
PRODUCTS = {
    'tshirt': {
        'id': 71,  # Bella + Canvas 3001 Unisex Short Sleeve Jersey T-Shirt
        'name': 'Bella + Canvas 3001'
    },
    'hoodie': {
        'id': 146,  # Gildan 18500 Unisex Heavy Blend Hooded Sweatshirt
        'name': 'Gildan 18500'
    },
    'sweatshirt': {
        'id': 146,  # Gildan 18500 (stesso modello hoodie)
        'name': 'Gildan 18500'
    }
}

# ==================== ONLYONE WORKFLOW CONFIG ====================

# Canvas Templates (12x16 inches @300 DPI = 3600x4800 pixels)
CANVAS_TEMPLATES = {
    'main': {
        'width': 3600,
        'height': 4800,
        'dpi': 300,
        'safe_margin': 75  # 0.25 inch in pixels
    },
    'sleeve': {
        'width': 900,   # 3 inches
        'height': 4200, # 14 inches
        'dpi': 300,
        'safe_margin': 75
    }
}

# Layout Percentages (basato sulla preview OnlyOne)
LAYOUT_CONFIG = {
    'front': {
        'main_image': {
            'width_percent': 45,      # Design principale dimensione media
            'top_percent': 20,        # Posizionato in alto
        },
        'title': {
            'width_percent': 60,      # Titolo curvato più largo
            'top_percent': 55,        # Sotto il design principale
        },
        'wordmark': {
            'width_percent': 25,      # "The Only One" corsivo
            'top_percent': 75,        # In fondo alla composizione
        }
    },
    'back': {
        'main_image': {
            'width_percent': 80,      # 75-90% range - design grande
            'top_percent': 50,        # Centrato verticalmente
        }
    },
    'sleeve': {
        'logo': {
            'height_percent': 25,     # 20-30% range
            'top_percent': 50,        # Centrato verticalmente
        }
    }
}

# Color Mapping per Contrasto
LIGHT_COLORS = [
    "White", "Natural", "Sand", "Ash", "Sport Grey", "Cream",
    "Ivory", "Beige", "Yellow", "Light Pink", "Light Gray", 
    "Light Grey", "Tan", "Khaki", "Silver"
]

DARK_COLORS = [
    "Black", "Charcoal", "Navy", "Forest", "Maroon", 
    "Dark Grey", "Dark Gray", "Midnight", "Heather"
]

# Colori per testo/loghi
CONTRAST_COLORS = {
    'dark_text': '#111111',    # Per capi chiari
    'light_text': '#FFFFFF'    # Per capi scuri
}

# ==================== ASSETS PATHS ====================

# Directories
UPSCALED_DIR = "upscaled"
TITOLI_DIR = "Titoli"
ASSETS_DIR = "assets"
ARTIFACTS_DIR = "artifacts"

# Assets sub-directories
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
WORDMARKS_DIR = os.path.join(ASSETS_DIR, "wordmarks")
TEMPLATES_DIR = os.path.join(ASSETS_DIR, "templates")

# Font Configuration  
LIBRE_BODONI_FONT = {
    'regular': os.path.join(FONTS_DIR, "Libre_Bodoni", "static", "LibreBodoni-Regular.ttf"),
    'medium': os.path.join(FONTS_DIR, "Libre_Bodoni", "static", "LibreBodoni-Medium.ttf"),
    'bold': os.path.join(FONTS_DIR, "Libre_Bodoni", "static", "LibreBodoni-Bold.ttf"),
    'tracking': 0.05,  # Tracking leggero positivo
    'curve': -0.60     # Curvatura standard
}

# Wordmark Assets
WORDMARK_ASSETS = {
    'dark': os.path.join(WORDMARKS_DIR, "too_dark.png"),    # #111111
    'light': os.path.join(WORDMARKS_DIR, "too_light.png")   # #FFFFFF
}

# Logo Assets (esistenti - manteniamo compatibilità)
LOGO_WHITE_PATH = "generate/logo_white.png"
LOGO_BLACK_PATH = "generate/logo_black.png"
N1_WHITE_PATH = "generate/n1_white.png"
N1_BLACK_PATH = "generate/n1_black.png"
TEXT_LIGHTGRAY_PATH = "generate/the_only_one_text_lightgray.png"
TEXT_DARKGRAY_PATH = "generate/the_only_one_text_darkgray.png"

# ==================== VALIDATION CONFIG ====================

# Requisiti immagini input
IMAGE_REQUIREMENTS = {
    'format': 'PNG',
    'transparency': True,
    'color_profile': 'sRGB',
    'min_dpi': 300,
    'min_dimension': 1024,  # pixel lato lungo se DPI non disponibile
    'max_file_size': 200 * 1024 * 1024,  # 200MB
    'clean_border': True,   # Pulisci aloni 1-2px
    'border_threshold': 2   # pixel
}

# QA Thresholds
QA_CONFIG = {
    'max_scaling': 100,     # % massimo scaling
    'min_contrast_ratio': 3.0,  # WCAG-like per leggibilità
    'alignment_tolerance': 2,    # pixel di tolleranza centratura
    'quality_score_min': 80     # Score minimo per passare QA
}

# ==================== CSV TRACKING SCHEMA ====================

CSV_TRACKING_PATH = "onlyone_tracking.csv"
CSV_SCHEMA = [
    'slug',              # cavallo-spettrale
    'artwork_url',       # URL immagine principale
    'title',             # "Cavallo Spettrale" (3-4 parole max)
    'title_dark_url',    # URL titolo scuro (#111)
    'title_light_url',   # URL titolo chiaro (#FFF)
    'too_dark_url',      # URL wordmark scuro
    'too_light_url',     # URL wordmark chiaro  
    'front_light_url',   # URL composizione front per capi chiari
    'front_dark_url',    # URL composizione front per capi scuri
    'back_url',          # URL composizione back (universale)
    'sleeve_dark_url',   # URL sleeve per capi chiari (logo scuro)
    'sleeve_light_url',  # URL sleeve per capi scuri (logo chiaro)
    'product_type',      # tshirt/hoodie/sweatshirt
    'colors_light',      # Lista colori chiari abilitati
    'colors_dark',       # Lista colori scuri abilitati
    'sizes',             # S,M,L,XL,XXL
    'price',             # Prezzo uniform
    'product_id',        # ID Printful
    'store_url',         # URL pubblico prodotto
    'status',            # draft/published/archived
    'timestamp'          # Data creazione
]

# ==================== BUSINESS CONFIG ====================

# Pricing
DEFAULT_PRICE = "35.00"
BRAND_NAME = "OnlyOne"

# Product Title Template
PRODUCT_TITLE_TEMPLATE = "OnlyOne — {title}"

# Description Template
PRODUCT_DESCRIPTION_TEMPLATE = """OnlyOne — {title}

Un'opera unica, creata una sola volta.
Non appena diventa tua, sparisce per sempre dallo store.

Materiali premium, stampa di qualità museale.
Edizione limitata: solo 1 pezzo disponibile.

{title} è destinato a restare unico.
Solo chi lo sceglie entra nella storia di OnlyOne.

— The Only One —"""

# ==================== LEGACY COMPATIBILITY ====================

# Manteniamo configurazioni esistenti per compatibilità
RESULTS_CSV_PATH = "printful_results.csv"  # Vecchio CSV
PRINT_AREA_WIDTH = 4500
PRINT_AREA_HEIGHT = 5100
TARGET_COVERAGE = 0.85
RATE_LIMIT_CALLS = 120
RATE_LIMIT_PERIOD = 60
# products/hoodie.py - Versione aggiornata per OnlyOne
from typing import Dict, List
from .base_product import BaseProduct

class HoodieProduct(BaseProduct):
    """Hoodie OnlyOne con composizioni pre-generate"""
    
    def __init__(self):
        super().__init__(
            product_id=146,  # Gildan 18500
            product_name="Hoodie"
        )
        
    def get_print_files(self, variant_id: int, color: str,
                        image_urls: Dict, elements: Dict) -> List[Dict]:
        """
        METODO LEGACY - Mantienuto per compatibilità.
        
        Configurazione originale Hoodie con URL pubbliche.
        DEPRECATO: Usa get_print_files_composite() nella classe base.
        """
        print("⚠️ Usando metodo legacy get_print_files() per Hoodie")
        
        files = []
        
        # 1. Immagine principale - fronte (OBBLIGATORIA)
        if 'main' in image_urls:
            files.append({
                "url": image_urls['main'],
                "placement": "front"
            })
            print(f"    📄 Principale: OK")
        else:
            raise ValueError("URL immagine principale mancante")
        
        # 2. Logo sul retro (opzionale)
        logo_key = elements.get('logo_key')
        if logo_key and logo_key in image_urls:
            files.append({
                "url": image_urls[logo_key],
                "placement": "back"
            })
            print(f"    📄 Logo: OK")
        
        # 3. Titolo sul cappuccio (opzionale)
        title_key = elements.get('title_key')
        if title_key and title_key in image_urls:
            files.append({
                "url": image_urls[title_key], 
                "placement": "front"
            })
            print(f"    📄 Titolo: OK")
        
        print(f"    ✅ {len(files)} file per {color}")
        return files
    
    def get_printful_placement_mapping(self) -> Dict[str, str]:
        """
        Mapping placement OnlyOne → Printful per Hoodie.
        
        Returns:
            Dict con mapping placement
        """
        return {
            'front': 'front',           # Composizione front → front Printful
            'back': 'back',             # Composizione back → back Printful  
            'sleeve': 'left_sleeve'     # Composizione sleeve → left_sleeve Printful
        }
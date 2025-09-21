# products/tshirt.py - Versione Back DTG + Front/Sleeve Embroidery
from typing import Dict, List
from .base_product import BaseProduct

class TShirtProduct(BaseProduct):
    """T-Shirt con configurazione Back DTG + Front/Sleeve Embroidery"""
    
    def __init__(self):
        super().__init__(
            product_id=71,  # Bella + Canvas 3001
            product_name="T-Shirt"
        )
        
    def get_print_files(self, variant_id: int, color: str,
                        image_urls: Dict, elements: Dict) -> List[Dict]:
        """
        Configura file per T-Shirt con:
        - Front: Ricamo grigio (da cartella ricamo/)
        - Back: DTG full size centrato (design originale)  
        - Sleeve: Ricamo logo grigio grande e basso
        """
        files = []
        
        # FRONT: Ricamo grigio (versione semplificata)
        if 'front_embroidery' in image_urls:
            files.append({
                "url": image_urls['front_embroidery'],
                "placement": "embroidery_chest"
            })
            print(f"    📍 Front embroidery: OK")
        else:
            print(f"    ⚠️ Front embroidery mancante")
        
        # BACK: DTG full size centrato (design originale complesso)
        if 'main' in image_urls:
            files.append({
                "url": image_urls['main'],
                "placement": "back"
            })
            print(f"    📍 Back DTG: OK")
        else:
            print(f"    ⚠️ Back DTG mancante")
        
        # SLEEVE: Ricamo logo universale grigio
        if 'universal_logo' in image_urls:
            files.append({
                "url": image_urls['universal_logo'],
                "placement": "embroidery_left_sleeve"
            })
            print(f"    📍 Sleeve embroidery: OK")
        else:
            print(f"    ⚠️ Sleeve embroidery mancante")
        
        print(f"    ✅ {len(files)} file configurati per {color}")
        return files
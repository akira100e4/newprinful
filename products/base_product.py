# products/base_product.py - Versione aggiornata per OnlyOne workflow
import os
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from api.printful_api import PrintfulAPI
from utils.text_utils import is_light_color, create_product_description, create_product_title

class BaseProduct(ABC):
    """Classe base per prodotti Printful con OnlyOne workflow avanzato"""
    
    def __init__(self, product_id: int, product_name: str):
        self.product_id = product_id
        self.product_name = product_name
        self.variants_cache = None
        
    @abstractmethod
    def get_print_files(self, variant_id: int, color: str, image_urls: Dict, elements: Dict) -> List[Dict]:
        """Metodo legacy per compatibilità - DA DEPRECARE"""
        pass
    
    def load_variants(self, api: PrintfulAPI) -> List[Dict]:
        """Carica varianti con cache"""
        if self.variants_cache is None:
            print(f"📡 Caricando varianti prodotto {self.product_id}...")
            response = api.get_catalog_product(self.product_id)
            self.variants_cache = response.get('result', {}).get('variants', [])
            print(f"✅ {len(self.variants_cache)} varianti caricate")
        return self.variants_cache
    
    def filter_variants_by_color(self, variants: List[Dict], colors: List[str]) -> List[Dict]:
        """Filtra varianti per colori"""
        color_set = set(colors)
        filtered = [v for v in variants if v.get('color') in color_set]
        print(f"🎨 {len(filtered)}/{len(variants)} varianti per colori selezionati")
        return filtered
    
    def get_asset_set_for_color(self, color: str) -> str:
        """
        Determina quale set di asset usare basato sul colore capo.
        
        Args:
            color: Nome colore variante Printful
            
        Returns:
            'light' per capi chiari (usa elementi scuri)
            'dark' per capi scuri (usa elementi chiari)  
        """
        from config_printful import LIGHT_COLORS
        return 'light' if color in LIGHT_COLORS else 'dark'
    
    def get_print_files_composite(self, variant_id: int, color: str, 
                                 composition_urls: Dict[str, str]) -> List[Dict]:
        """
        Crea print files usando composizioni pre-generate.
        FIXED: Invia solo placement appropriato per il colore specifico della variante.
        
        Args:
            variant_id: ID variante Printful
            color: Nome colore variante
            composition_urls: Dict con URL composizioni uploadate
                
        Returns:
            Lista configurazioni print files per Printful
        """
        files = []
        
        # Determina set asset per contrasto
        asset_set = self.get_asset_set_for_color(color)
        
        print(f"    🎨 {color} → asset set '{asset_set}'")
        
        # FRONT - usa composizione appropriata per contrasto del colore
        front_key = f'front_{asset_set}'
        if front_key in composition_urls and composition_urls[front_key]:
            files.append({
                "url": composition_urls[front_key],
                "placement": "front"
            })
            print(f"      ✅ Front: {front_key}")
        else:
            print(f"      ⚠️ Front mancante: {front_key}")
        
        # BACK - composizione universale (solo per prima variante per evitare duplicati)
        # Printful interpreta placement duplicati come errore, quindi invio back solo una volta
        if 'back' in composition_urls and composition_urls['back']:
            files.append({
                "url": composition_urls['back'],
                "placement": "back"
            })
            print(f"      ✅ Back: universale")
        else:
            print(f"      ⚠️ Back mancante")
        
        print(f"    📄 {len(files)} file configurati per {color}")
        return files
    
    async def create_product_advanced(self, api: PrintfulAPI, uploader,
                                    main_image_path: str, composition_paths: Dict[str, str],
                                    tracker = None, selected_colors: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Crea prodotto usando workflow OnlyOne avanzato.
        
        Args:
            api: Client API Printful
            uploader: Uploader per URL pubbliche (Imgur, etc.)
            main_image_path: Path immagine principale
            composition_paths: Dict con path composizioni generate dal Canvas Composer
            tracker: OnlyOneTracker per aggiornamenti (opzionale)
            selected_colors: Lista colori da usare
            
        Returns:
            Dict con risultato creazione prodotto
        """
        from utils.text_utils import normalize_product_name
        
        try:
            print(f"\n🚀 CREAZIONE PRODOTTO AVANZATA: {self.product_name}")
            print("="*50)
            
            start_time = __import__('time').time()
            
            # 1. Genera slug per tracking
            slug = normalize_product_name(os.path.basename(main_image_path))
            from utils.text_utils import generate_kebab_slug
            slug = generate_kebab_slug(slug)
            
            print(f"🏷️ Slug prodotto: {slug}")
            
            # 2. Gestione URL composizioni (già uploadate o da uploadare)
            composition_urls = {}
            upload_errors = []
            
            # Controlla se composition_paths contiene già URL (da Step 6) o path locali
            for comp_type, comp_value in composition_paths.items():
                if comp_value:
                    if comp_value.startswith('http'):
                        # È già un URL da Step 6 precedente
                        composition_urls[comp_type] = comp_value
                        print(f"  ✅ {comp_type}: URL esistente")
                    elif os.path.exists(comp_value):
                        # È un path locale, uploada ora
                        try:
                            if hasattr(uploader, 'upload_image'):
                                url = uploader.upload_image(comp_value)
                            else:
                                url = uploader.get_public_url(comp_value)
                            
                            composition_urls[comp_type] = url
                            print(f"  ✅ {comp_type}: {os.path.basename(comp_value)}")
                            
                        except Exception as e:
                            upload_errors.append(f"{comp_type}: {e}")
                            print(f"  ❌ {comp_type}: {e}")
                    else:
                        upload_errors.append(f"{comp_type}: file/URL non trovato")
                        print(f"  ⚠️ {comp_type}: file/URL non trovato")
            
            if not composition_urls:
                raise Exception("Nessuna composizione disponibile")
            
            # Aggiorna tracker con URL composizioni
            if tracker:
                tracker.update_composition_paths(slug, composition_urls)
            
            # 3. Carica e filtra varianti
            all_variants = self.load_variants(api)
            
            if selected_colors:
                variants = self.filter_variants_by_color(all_variants, selected_colors)
                if not variants:
                    raise ValueError(f"Nessuna variante per colori: {selected_colors}")
            else:
                # Default: solo Black e White per test rapidi
                default_colors = ['Black', 'White']
                variants = self.filter_variants_by_color(all_variants, default_colors)
                print(f"📦 Uso colori default: {default_colors}")
            
            # 4. Prepara dati prodotto
            base_name = slug.replace('-', ' ').title()
            
            product_data = {
                "sync_product": {
                    "name": create_product_title(base_name, self.product_name.lower())
                },
                "sync_variants": []
            }
            
            # 5. Genera varianti con print files per colore
            print(f"🔧 Configurando {len(variants)} varianti...")
            
            for variant in variants:
                color = variant.get('color')
                variant_id = variant.get('id')
                asset_set = self.get_asset_set_for_color(color)
                
                print(f"    🎨 Variante: {color} (ID: {variant_id}) → {asset_set}")
                
                # Crea file specifici per questa variante/colore
                variant_files = []
                
                # Front: scegli la composizione giusta per il colore
                front_key = f'front_{asset_set}'
                if front_key in composition_urls and composition_urls[front_key]:
                    variant_files.append({
                        "url": composition_urls[front_key],
                        "placement": "front"
                    })
                    print(f"      ✅ Front: {front_key}")
                
                # Back: stesso per tutti (ma ogni variante deve specificarlo)
                if 'back' in composition_urls:
                    variant_files.append({
                        "url": composition_urls['back'],
                        "placement": "back"
                    })
                    print(f"      ✅ Back: universale")
                
                if variant_files:
                    product_data["sync_variants"].append({
                        "variant_id": variant_id,
                        "retail_price": "35.00",
                        "files": variant_files
                    })
                    print(f"      📄 {len(variant_files)} file per variante")
                else:
                    print(f"      ⚠️ Nessun file per {color}")
            
            if not product_data["sync_variants"]:
                raise Exception("Nessuna variante configurata con successo")
            
            # 6. Invia a Printful
            print(f"📡 Invio a Printful ({len(product_data['sync_variants'])} varianti)...")
            response = api.create_sync_product(product_data)
            
            elapsed = __import__('time').time() - start_time
            
            # 7. Processa risposta
            if 'result' in response:
                product_id = response['result']['id']
                product_name = product_data["sync_product"]["name"]
                
                print(f"✅ PRODOTTO CREATO in {elapsed:.1f}s")
                print(f"   🆔 ID: {product_id}")
                print(f"   📝 Nome: {product_name}")
                print(f"   🎨 Varianti: {len(product_data['sync_variants'])}")
                
                # Risultato successo
                result = {
                    'success': True,
                    'product_id': product_id,
                    'product_name': product_name,
                    'variants_count': len(product_data['sync_variants']),
                    'duration': elapsed,
                    'upload_errors': upload_errors,
                    'slug': slug,
                    'composition_urls': composition_urls
                }
                
                # Aggiorna tracker con pubblicazione
                if tracker:
                    publish_data = {
                        'product_type': self.product_name.lower(),
                        'product_id': str(product_id),
                        'price': '35.00',
                        'colors_light': ','.join([v.get('color') for v in variants if self.get_asset_set_for_color(v.get('color')) == 'light']),
                        'colors_dark': ','.join([v.get('color') for v in variants if self.get_asset_set_for_color(v.get('color')) == 'dark']),
                        'sizes': 'S,M,L,XL,XXL'
                    }
                    tracker.mark_published(slug, publish_data)
                
                return result
                
            else:
                print(f"❌ CREAZIONE FALLITA in {elapsed:.1f}s")
                print(f"   Errore: {response}")
                
                return {
                    'success': False,
                    'error': response,
                    'duration': elapsed,
                    'upload_errors': upload_errors,
                    'slug': slug
                }
                
        except Exception as e:
            elapsed = __import__('time').time() - start_time if 'start_time' in locals() else 0
            
            print(f"❌ ERRORE CREAZIONE in {elapsed:.1f}s: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'duration': elapsed,
                'image_name': os.path.basename(main_image_path),
                'product_type': self.product_name
            }
    
    # ==================== METODI LEGACY (Compatibilità) ====================
    
    def get_contrast_elements(self, color: str) -> Dict[str, str]:
        """
        DEPRECATO: Usa get_asset_set_for_color() instead.
        Mantienuto per compatibilità con codice esistente.
        """
        print("⚠️ get_contrast_elements() è deprecato, usa get_asset_set_for_color()")
        
        if is_light_color(color):
            return {
                'logo_key': 'logo_black',
                'n1_key': 'n1_black', 
                'text_key': 'text_dark',
                'title_key': 'title_black'
            }
        else:
            return {
                'logo_key': 'logo_white',
                'n1_key': 'n1_white',
                'text_key': 'text_light', 
                'title_key': 'title_white'
            }
    
    async def create_product(self, api: PrintfulAPI, image_server,
                            main_image_path: str,
                            title_paths: Optional[Dict] = None,
                            selected_colors: Optional[List[str]] = None) -> Dict:
        """
        DEPRECATO: Metodo legacy con image_server.
        Mantienuto per compatibilità. Usa create_product_advanced().
        """
        print("⚠️ create_product() è deprecato, usa create_product_advanced()")
        
        try:
            print(f"\n🚀 CREAZIONE {self.product_name.upper()} (LEGACY)")
            
            # Prepara URL immagine principale
            main_url = image_server.get_image_url(main_image_path)
            
            # Prepara URL elementi aggiuntivi
            image_urls = {'main': main_url}
            
            # URL elementi statici (legacy)
            from config_printful import (
                LOGO_WHITE_PATH, LOGO_BLACK_PATH,
                N1_WHITE_PATH, N1_BLACK_PATH,
                TEXT_LIGHTGRAY_PATH, TEXT_DARKGRAY_PATH
            )
            
            static_mapping = {
                'logo_white': LOGO_WHITE_PATH,
                'logo_black': LOGO_BLACK_PATH,
                'n1_white': N1_WHITE_PATH,
                'n1_black': N1_BLACK_PATH,
                'text_light': TEXT_LIGHTGRAY_PATH,
                'text_dark': TEXT_DARKGRAY_PATH
            }
            
            for key, path in static_mapping.items():
                try:
                    if os.path.exists(path):
                        image_urls[key] = image_server.get_image_url(path)
                except:
                    pass
            
            # URL titoli personalizzati
            if title_paths:
                for color, path in title_paths.items():
                    try:
                        image_urls[f'title_{color}'] = image_server.get_image_url(path)
                    except:
                        pass
            
            print(f"🖼️ {len(image_urls)} URL preparati")
            
            # Resto della logica legacy...
            all_variants = self.load_variants(api)
            
            if selected_colors:
                variants = self.filter_variants_by_color(all_variants, selected_colors)
            else:
                variants = all_variants[:10]
            
            from utils.text_utils import normalize_product_name
            base_name = normalize_product_name(os.path.basename(main_image_path))
            
            product_data = {
                "sync_product": {
                    "name": create_product_title(base_name, self.product_name.lower())
                },
                "sync_variants": []
            }
            
            # Usa metodo legacy
            for variant in variants:
                color = variant.get('color')
                elements = self.get_contrast_elements(color)
                
                print_files = self.get_print_files(
                    variant['id'], color, image_urls, elements
                )
                
                product_data["sync_variants"].append({
                    "variant_id": variant['id'],
                    "retail_price": "35.00",
                    "files": print_files
                })
            
            response = api.create_sync_product(product_data)
            
            if 'result' in response:
                return {
                    'success': True,
                    'product_id': response['result']['id'],
                    'product_name': product_data["sync_product"]["name"],
                    'variants_count': len(variants)
                }
            else:
                return {
                    'success': False,
                    'error': response
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
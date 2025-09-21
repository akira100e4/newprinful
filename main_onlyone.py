# main_onlyone.py - OnlyOne Workflow Orchestrator Completo
import os
import glob
import asyncio
import time
from typing import List, Dict, Optional
from datetime import datetime

# Core imports
from api.printful_api import PrintfulAPI
from products import create_product
from utils.imgur_uploader import ImgurUploader
from utils.canvas_composer import CanvasComposer
from utils.font_renderer import batch_generate_titles_for_images
from utils.advanced_tracker import OnlyOneTracker, batch_create_entries
from utils.image_utils import validate_onlyone_image, clean_border_artifacts
from utils.text_utils import generate_kebab_slug, extract_title_from_slug
from processors.qa_validator import OnlyOneQAValidator, run_batch_qa_validation
from config_printful import (
    PRINTFUL_API_KEY, PRINTFUL_STORE_ID, UPSCALED_DIR, ARTIFACTS_DIR,
    WORDMARK_ASSETS, LOGO_WHITE_PATH, LOGO_BLACK_PATH
)

class OnlyOneCreator:
    """
    Orchestratore completo per workflow OnlyOne.
    Integra tutti i sistemi: validation, rendering, composition, upload, tracking.
    """
    
    def __init__(self):
        self.api = PrintfulAPI(PRINTFUL_API_KEY, PRINTFUL_STORE_ID)
        self.uploader = ImgurUploader()
        self.composer = CanvasComposer()
        self.tracker = OnlyOneTracker()
        self.qa_validator = OnlyOneQAValidator()
        
        # Statistiche sessione
        self.session_stats = {
            'start_time': time.time(),
            'images_processed': 0,
            'titles_generated': 0,
            'compositions_created': 0,
            'products_created': 0,
            'errors': []
        }
        
    def get_image_files(self) -> List[str]:
        """Trova immagini PNG nella directory upscaled"""
        patterns = [f"{UPSCALED_DIR}/*.png", f"{UPSCALED_DIR}/*.jpg"]
        images = []
        
        for pattern in patterns:
            images.extend(glob.glob(pattern))
        
        print(f"🖼️ Trovate {len(images)} immagini in {UPSCALED_DIR}/")
        
        if images:
            print("📁 Immagini trovate:")
            for img in images:
                print(f"  • {os.path.basename(img)}")
        
        return images
    
    def validate_input_images(self, image_files: List[str]) -> Dict[str, List[str]]:
        """
        Valida immagini input secondo specifiche OnlyOne.
        
        Returns:
            Dict con 'valid' e 'invalid' image lists
        """
        print(f"\n🔍 VALIDAZIONE INPUT - {len(image_files)} immagini")
        print("="*50)
        
        valid_images = []
        invalid_images = []
        
        for image_path in image_files:
            validation = validate_onlyone_image(image_path)
            
            if validation['valid']:
                valid_images.append(image_path)
                
                # Pulizia automatica bordi se richiesto
                from config_printful import IMAGE_REQUIREMENTS
                if IMAGE_REQUIREMENTS.get('clean_border', False):
                    clean_border_artifacts(image_path, 
                                         IMAGE_REQUIREMENTS.get('border_threshold', 2))
            else:
                invalid_images.append(image_path)
                self.session_stats['errors'].extend(validation['issues'])
        
        print(f"\n📊 Risultati validazione:")
        print(f"  ✅ Valide: {len(valid_images)}")
        print(f"  ❌ Invalide: {len(invalid_images)}")
        
        if invalid_images:
            print(f"  🚫 Immagini invalide:")
            for img in invalid_images:
                print(f"    • {os.path.basename(img)}")
        
        return {
            'valid': valid_images,
            'invalid': invalid_images
        }
    
    def setup_asset_library(self) -> Dict[str, str]:
        """
        Prepara libreria asset statici (wordmarks, loghi).
        
        Returns:
            Dict con path asset disponibili
        """
        print(f"\n📚 SETUP ASSET LIBRARY")
        print("="*30)
        
        assets = {}
        
        # Wordmarks "The Only One"
        for key, path in WORDMARK_ASSETS.items():
            if os.path.exists(path):
                assets[f'wordmark_{key}'] = path
                print(f"  ✅ Wordmark {key}: {os.path.basename(path)}")
            else:
                print(f"  ⚠️ Wordmark {key} mancante: {path}")
        
        # Loghi OnlyOne
        logo_mapping = {
            'logo_light': LOGO_WHITE_PATH,
            'logo_dark': LOGO_BLACK_PATH
        }
        
        for key, path in logo_mapping.items():
            if os.path.exists(path):
                assets[key] = path
                print(f"  ✅ Logo {key}: {os.path.basename(path)}")
            else:
                print(f"  ⚠️ Logo {key} mancante: {path}")
        
        print(f"  📦 Asset disponibili: {len(assets)}")
        return assets
    
    def upload_static_assets(self, assets: Dict[str, str]) -> Dict[str, str]:
        """
        Upload asset statici una volta sola.
        
        Returns:
            Dict con URL asset uploadati
        """
        print(f"\n📤 UPLOAD ASSET STATICI")
        print("="*30)
        
        uploaded_assets = {}
        
        for asset_key, asset_path in assets.items():
            try:
                url = self.uploader.upload_image(asset_path, f"onlyone_{asset_key}")
                uploaded_assets[asset_key] = url
                print(f"  ✅ {asset_key}: OK")
                
                # Pausa per rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ❌ {asset_key}: {e}")
                self.session_stats['errors'].append(f"Upload {asset_key}: {e}")
        
        print(f"  🌐 {len(uploaded_assets)} asset uploadati")
        return uploaded_assets
    
    async def process_single_image(self, image_path: str, static_assets: Dict[str, str],
                                  product_types: List[str] = ['tshirt']) -> Dict[str, any]:
        """
        Processa una singola immagine attraverso tutto il workflow OnlyOne.
        
        Args:
            image_path: Path immagine da processare
            static_assets: Dict con URL asset statici già uploadati
            product_types: Lista tipi prodotto da creare
            
        Returns:
            Dict con risultati processing
        """
        filename = os.path.basename(image_path)
        slug = generate_kebab_slug(filename)
        title = extract_title_from_slug(slug)
        
        print(f"\n🎨 PROCESSING: {filename}")
        print(f"    🏷️ Slug: {slug}")
        print(f"    📝 Titolo: {title}")
        print("="*50)
        
        result = {
            'image_path': image_path,
            'slug': slug,
            'title': title,
            'success': False,
            'steps_completed': [],
            'errors': [],
            'products_created': []
        }
        
        try:
            step_start = time.time()
            
            # 1. Crea entry nel tracker
            print(f"📋 Step 1: Creazione entry tracker...")
            if self.tracker.create_entry(slug, title):
                result['steps_completed'].append('tracker_entry')
                print(f"    ✅ Entry creato per {slug}")
            else:
                print(f"    ℹ️ Entry già esistente per {slug}")
            
            # 2. Genera titoli curvati
            print(f"🎨 Step 2: Generazione titoli Libre Bodoni...")
            from utils.font_renderer import render_title_with_libre_bodoni
            
            title_result = render_title_with_libre_bodoni(title, ARTIFACTS_DIR)
            
            if title_result['dark'] and title_result['light']:
                result['steps_completed'].append('titles_generated')
                result['title_paths'] = title_result
                print(f"    ✅ Titoli generati")
                self.session_stats['titles_generated'] += 1
            else:
                raise Exception("Generazione titoli fallita")
            
            # 3. Upload titoli
            print(f"📤 Step 3: Upload titoli...")
            title_urls = {}
            
            for variant, path in [('dark', title_result['dark']), ('light', title_result['light'])]:
                if path and os.path.exists(path):
                    url = self.uploader.upload_image(path, f"{slug}_title_{variant}")
                    title_urls[f'title_{variant}_url'] = url
                    time.sleep(0.5)  # Rate limiting
            
            if len(title_urls) == 2:
                result['steps_completed'].append('titles_uploaded')
                result['title_urls'] = title_urls
                print(f"    ✅ Titoli uploadati")
            else:
                raise Exception("Upload titoli fallito")
            
            # 4. Prepara asset set completo
            print(f"🧩 Step 4: Preparazione asset set...")
            complete_assets = {
                **static_assets,
                **title_urls,
                'artwork_url': self.uploader.upload_image(image_path, f"{slug}_main")
            }
            
            # Aggiorna tracker con asset URLs
            self.tracker.update_asset_urls(slug, complete_assets)
            result['steps_completed'].append('assets_prepared')
            print(f"    ✅ Asset set completo: {len(complete_assets)} elementi")
            
            # 5. Genera composizioni Canvas
            print(f"🎭 Step 5: Composizione Canvas...")
            
            # Prepara path locali per composizioni
            asset_paths = {
                'title_dark': title_result['dark'],
                'title_light': title_result['light'],
                'wordmark_dark': static_assets.get('wordmark_dark'),
                'wordmark_light': static_assets.get('wordmark_light'),
                'logo_dark': static_assets.get('logo_dark'),
                'logo_light': static_assets.get('logo_light')
            }
            
            composition_paths = self.composer.create_all_variants_for_product(
                slug, image_path, asset_paths, ARTIFACTS_DIR
            )
            
            successful_compositions = [k for k, v in composition_paths.items() if v is not None]
            if len(successful_compositions) >= 3:  # Minimo front_light, front_dark, back
                result['steps_completed'].append('compositions_created')
                result['composition_paths'] = composition_paths
                print(f"    ✅ {len(successful_compositions)}/5 composizioni create")
                self.session_stats['compositions_created'] += 1
            else:
                raise Exception(f"Solo {len(successful_compositions)}/5 composizioni create")
            
            # 6. Upload composizioni
            print(f"📤 Step 6: Upload composizioni...")
            composition_urls = {}
            
            for comp_type, comp_path in composition_paths.items():
                if comp_path and os.path.exists(comp_path):
                    try:
                        url = self.uploader.upload_image(comp_path, f"{slug}_{comp_type}")
                        composition_urls[comp_type] = url
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"      ⚠️ Upload {comp_type} fallito: {e}")
            
            if len(composition_urls) >= 3:
                result['steps_completed'].append('compositions_uploaded')
                result['composition_urls'] = composition_urls
                
                # Aggiorna tracker con URL (non path locali)
                self.tracker.update_composition_paths(slug, composition_urls)
                print(f"    ✅ {len(composition_urls)} composizioni uploadate")
            else:
                raise Exception("Upload composizioni insufficienti")
            
            # 7. QA Validation
            print(f"🔍 Step 7: QA Validation...")
            qa_report = self.qa_validator.run_full_qa_validation(
                slug, image_path, composition_paths
            )
            
            result['qa_report'] = qa_report
            result['steps_completed'].append('qa_validated')
            
            if qa_report['overall_valid']:
                print(f"    ✅ QA Score: {qa_report['overall_score']:.1f}/100")
            else:
                print(f"    ⚠️ QA Issues: {qa_report['summary']['total_issues']} errori")
            
            # 8. Creazione prodotti Printful
            print(f"🚀 Step 8: Creazione prodotti Printful...")
            
            for product_type in product_types:
                try:
                    product = create_product(product_type)
                    
                    product_result = await product.create_product_advanced(
                        self.api, self.uploader, image_path, 
                        composition_urls, self.tracker  # Passa URL, non path locali
                    )
                    
                    if product_result['success']:
                        result['products_created'].append({
                            'type': product_type,
                            'id': product_result['product_id'],
                            'name': product_result['product_name'],
                            'variants': product_result['variants_count']
                        })
                        print(f"    ✅ {product_type.title()}: ID {product_result['product_id']}")
                        self.session_stats['products_created'] += 1
                    else:
                        error_msg = f"{product_type}: {product_result.get('error', 'Unknown error')}"
                        result['errors'].append(error_msg)
                        print(f"    ❌ {error_msg}")
                        
                    # Pausa tra prodotti
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    error_msg = f"Errore creazione {product_type}: {e}"
                    result['errors'].append(error_msg)
                    print(f"    ❌ {error_msg}")
            
            if result['products_created']:
                result['steps_completed'].append('products_created')
                result['success'] = True
                print(f"    🎉 {len(result['products_created'])} prodotti creati!")
            
            # Timing
            total_time = time.time() - step_start
            result['processing_time'] = total_time
            
            print(f"\n✅ PROCESSING COMPLETATO in {total_time:.1f}s")
            print(f"   📦 Steps: {len(result['steps_completed'])}/8")
            print(f"   🚀 Prodotti: {len(result['products_created'])}")
            
            self.session_stats['images_processed'] += 1
            
        except Exception as e:
            result['errors'].append(str(e))
            self.session_stats['errors'].append(f"{slug}: {e}")
            print(f"\n❌ PROCESSING FALLITO: {e}")
        
        return result
    
    def print_session_summary(self):
        """Stampa summary finale della sessione"""
        elapsed = time.time() - self.session_stats['start_time']
        
        print(f"\n📊 SESSION SUMMARY")
        print("="*40)
        print(f"⏱️ Durata totale: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"🖼️ Immagini processate: {self.session_stats['images_processed']}")
        print(f"🎨 Titoli generati: {self.session_stats['titles_generated']}")
        print(f"🎭 Composizioni create: {self.session_stats['compositions_created']}")
        print(f"🚀 Prodotti creati: {self.session_stats['products_created']}")
        
        if self.session_stats['errors']:
            print(f"❌ Errori: {len(self.session_stats['errors'])}")
            print(f"   Primi 3 errori:")
            for error in self.session_stats['errors'][:3]:
                print(f"   • {error}")
        
        # Tracker summary
        self.tracker.print_summary()
        
        # Salva tracker
        self.tracker.save()
    
    async def run_workflow(self, workflow_type: str = 'complete'):
        """
        Esegue workflow OnlyOne completo.
        
        Args:
            workflow_type: 'test' | 'batch' | 'complete' | 'validation_only'
        """
        print(f"🚀 ONLYONE WORKFLOW: {workflow_type.upper()}")
        print(f"🕒 Avvio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        try:
            # 1. Setup iniziale
            images = self.get_image_files()
            if not images:
                print("❌ Nessuna immagine trovata")
                return
            
            # 2. Validazione input
            validation_result = self.validate_input_images(images)
            valid_images = validation_result['valid']
            
            if not valid_images:
                print("❌ Nessuna immagine valida")
                return
            
            # 3. Setup asset library
            static_assets_paths = self.setup_asset_library()
            static_assets_urls = self.upload_static_assets(static_assets_paths)
            
            if not static_assets_urls:
                print("❌ Upload asset statici fallito")
                return
            
            # 4. Selezione immagini da processare
            if workflow_type == 'test':
                selected_images = valid_images[:1]
                product_types = ['tshirt']
                print(f"🧪 Modalità test: 1 immagine, solo T-shirt")
            elif workflow_type == 'batch':
                selected_images = valid_images
                product_types = ['tshirt']
                print(f"📦 Modalità batch: {len(selected_images)} immagini, solo T-shirt")
            elif workflow_type == 'complete':
                selected_images = valid_images
                product_types = ['tshirt', 'hoodie']
                print(f"🎯 Modalità completa: {len(selected_images)} immagini, T-shirt + Hoodie")
            elif workflow_type == 'validation_only':
                print(f"🔍 Solo validazione completata")
                return
            else:
                selected_images = valid_images[:1]
                product_types = ['tshirt']
            
            # 5. Processing batch
            print(f"\n🔄 PROCESSING BATCH - {len(selected_images)} immagini")
            print("="*50)
            
            batch_results = []
            
            for i, image_path in enumerate(selected_images, 1):
                print(f"\n[{i}/{len(selected_images)}] Processing...")
                
                result = await self.process_single_image(
                    image_path, static_assets_urls, product_types
                )
                batch_results.append(result)
                
                # Pausa tra immagini
                if i < len(selected_images):
                    print(f"⏸️ Pausa 5s prima della prossima immagine...")
                    await asyncio.sleep(5)
            
            # 6. Summary finale
            self.print_session_summary()
            
            # 7. Report finale
            successful = sum(1 for r in batch_results if r['success'])
            print(f"\n🏁 WORKFLOW COMPLETATO!")
            print(f"✅ Successi: {successful}/{len(batch_results)}")
            print(f"📁 Risultati salvati in: {ARTIFACTS_DIR}/")
            print(f"📊 Tracking: {self.tracker.csv_path}")
            
        except KeyboardInterrupt:
            print(f"\n🛑 Workflow interrotto dall'utente")
            self.print_session_summary()
        except Exception as e:
            print(f"\n❌ Errore workflow: {e}")
            self.print_session_summary()

async def main():
    """Main interattivo per workflow OnlyOne"""
    
    print("🎨 ONLYONE WORKFLOW ORCHESTRATOR")
    print("="*50)
    print("🎯 Sistema completo: Validation → Titles → Canvas → Upload → Printful")
    print("="*50)
    
    creator = OnlyOneCreator()
    
    try:
        print("\n⚡ MODALITÀ DISPONIBILI:")
        print("1. 🧪 Test - 1 immagine, solo T-shirt")
        print("2. 📦 Batch T-shirt - Tutte le immagini, solo T-shirt") 
        print("3. 🎯 Completo - Tutte le immagini, T-shirt + Hoodie")
        print("4. 🔍 Solo Validazione - Controlla immagini senza creare prodotti")
        print("5. 📊 Status Tracker - Mostra stato tracking")
        
        choice = input("\n👉 Scelta (1-5): ").strip()
        
        if choice == '1':
            await creator.run_workflow('test')
        elif choice == '2':
            await creator.run_workflow('batch')
        elif choice == '3':
            await creator.run_workflow('complete')
        elif choice == '4':
            await creator.run_workflow('validation_only')
        elif choice == '5':
            creator.tracker.print_summary()
        else:
            print("❌ Scelta non valida")
            return
    
    except KeyboardInterrupt:
        print(f"\n👋 Arrivederci!")
    except Exception as e:
        print(f"\n❌ Errore main: {e}")

if __name__ == "__main__":
    asyncio.run(main())
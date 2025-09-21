# utils/canvas_composer.py - Canvas Composer per OnlyOne workflow
from PIL import Image, ImageDraw
import os
from typing import Dict, Tuple, Optional, List
import math

class CanvasComposer:
    """
    Composer per creare layout OnlyOne con front/back/sleeve.
    Compone tutti gli elementi in singoli PNG per upload Printful.
    """
    
    def __init__(self):
        from config_printful import CANVAS_TEMPLATES, LAYOUT_CONFIG
        self.canvas_templates = CANVAS_TEMPLATES
        self.layout_config = LAYOUT_CONFIG
        
    def calculate_position(self, canvas_size: Tuple[int, int], element_size: Tuple[int, int], 
                          position_config: Dict, alignment: str = 'center') -> Tuple[int, int]:
        """
        Calcola posizione elemento su canvas in base a configurazione percentuale.
        
        Args:
            canvas_size: (width, height) del canvas
            element_size: (width, height) dell'elemento
            position_config: Config con width_percent, top_percent, etc.
            alignment: 'center', 'left', 'right'
            
        Returns:
            (x, y) posizione top-left per paste()
        """
        canvas_w, canvas_h = canvas_size
        elem_w, elem_h = element_size
        
        # Posizione verticale da percentuale
        if 'top_percent' in position_config:
            y = int(canvas_h * position_config['top_percent'] / 100)
        else:
            y = (canvas_h - elem_h) // 2  # Centrato verticalmente
        
        # Posizione orizzontale
        if alignment == 'center':
            x = (canvas_w - elem_w) // 2
        elif alignment == 'left':
            x = int(canvas_w * 0.1)  # 10% da sinistra
        elif alignment == 'right':
            x = int(canvas_w * 0.9) - elem_w  # 10% da destra
        else:
            x = (canvas_w - elem_w) // 2
            
        return x, y
    
    def resize_maintaining_aspect(self, image: Image.Image, target_config: Dict, 
                                 canvas_size: Tuple[int, int]) -> Image.Image:
        """
        Ridimensiona immagine mantenendo aspect ratio secondo configurazione.
        
        Args:
            image: PIL Image da ridimensionare
            target_config: Config con width_percent o height_percent
            canvas_size: Dimensioni canvas di riferimento
            
        Returns:
            Immagine ridimensionata
        """
        canvas_w, canvas_h = canvas_size
        
        # Calcola dimensioni target da percentuale
        if 'width_percent' in target_config:
            target_width = int(canvas_w * target_config['width_percent'] / 100)
            # Calcola altezza mantenendo aspect ratio
            aspect_ratio = image.height / image.width
            target_height = int(target_width * aspect_ratio)
        elif 'height_percent' in target_config:
            target_height = int(canvas_h * target_config['height_percent'] / 100)
            # Calcola larghezza mantenendo aspect ratio
            aspect_ratio = image.width / image.height
            target_width = int(target_height * aspect_ratio)
        else:
            # Nessuna configurazione, mantieni dimensioni originali
            return image
        
        # Ridimensiona con alta qualità
        return image.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    def apply_safe_margins(self, position: Tuple[int, int], element_size: Tuple[int, int], 
                          canvas_size: Tuple[int, int], margin: int = 75) -> Tuple[int, int]:
        """
        Applica margini di sicurezza assicurando che l'elemento non esca dalla safe area.
        
        Args:
            position: (x, y) posizione calcolata
            element_size: (width, height) elemento
            canvas_size: (width, height) canvas
            margin: Margine in pixel (75px = 0.25")
            
        Returns:
            (x, y) posizione corretta dentro safe area
        """
        x, y = position
        elem_w, elem_h = element_size
        canvas_w, canvas_h = canvas_size
        
        # Assicura margine minimo dai bordi
        x = max(margin, min(x, canvas_w - elem_w - margin))
        y = max(margin, min(y, canvas_h - elem_h - margin))
        
        return x, y
    
    def compose_front(self, main_image_path: str, title_image_path: str, 
                     wordmark_image_path: str, output_path: str) -> bool:
        """
        Compone layout FRONT: Design → Titolo Curvato → Wordmark.
        
        Args:
            main_image_path: Path design principale
            title_image_path: Path titolo curvato (già generato)
            wordmark_image_path: Path wordmark "The Only One"
            output_path: Path output PNG composito
            
        Returns:
            True se successo
        """
        try:
            # Canvas principale 12x16" @300DPI
            template = self.canvas_templates['main']
            canvas_size = (template['width'], template['height'])
            safe_margin = template['safe_margin']
            
            # Crea canvas trasparente
            canvas = Image.new('RGBA', canvas_size, (255, 255, 255, 0))
            
            print(f"🎨 Composizione FRONT su canvas {canvas_size[0]}x{canvas_size[1]}px")
            
            # 1. DESIGN PRINCIPALE
            if os.path.exists(main_image_path):
                main_img = Image.open(main_image_path).convert('RGBA')
                main_config = self.layout_config['front']['main_image']
                
                # Ridimensiona secondo configurazione
                main_resized = self.resize_maintaining_aspect(main_img, main_config, canvas_size)
                
                # Calcola posizione
                main_pos = self.calculate_position(canvas_size, main_resized.size, main_config)
                main_pos = self.apply_safe_margins(main_pos, main_resized.size, canvas_size, safe_margin)
                
                # Componi su canvas
                canvas.paste(main_resized, main_pos, main_resized)
                print(f"  ✅ Design principale: {main_resized.size} @ {main_pos}")
            else:
                print(f"  ⚠️ Design principale non trovato: {main_image_path}")
            
            # 2. TITOLO CURVATO
            if os.path.exists(title_image_path):
                title_img = Image.open(title_image_path).convert('RGBA')
                title_config = self.layout_config['front']['title']
                
                # Ridimensiona se necessario
                title_resized = self.resize_maintaining_aspect(title_img, title_config, canvas_size)
                
                # Calcola posizione
                title_pos = self.calculate_position(canvas_size, title_resized.size, title_config)
                title_pos = self.apply_safe_margins(title_pos, title_resized.size, canvas_size, safe_margin)
                
                # Componi su canvas
                canvas.paste(title_resized, title_pos, title_resized)
                print(f"  ✅ Titolo curvato: {title_resized.size} @ {title_pos}")
            else:
                print(f"  ⚠️ Titolo non trovato: {title_image_path}")
            
            # 3. WORDMARK "THE ONLY ONE"
            if os.path.exists(wordmark_image_path):
                wordmark_img = Image.open(wordmark_image_path).convert('RGBA')
                wordmark_config = self.layout_config['front']['wordmark']
                
                # Ridimensiona
                wordmark_resized = self.resize_maintaining_aspect(wordmark_img, wordmark_config, canvas_size)
                
                # Calcola posizione
                wordmark_pos = self.calculate_position(canvas_size, wordmark_resized.size, wordmark_config)
                wordmark_pos = self.apply_safe_margins(wordmark_pos, wordmark_resized.size, canvas_size, safe_margin)
                
                # Componi su canvas
                canvas.paste(wordmark_resized, wordmark_pos, wordmark_resized)
                print(f"  ✅ Wordmark: {wordmark_resized.size} @ {wordmark_pos}")
            else:
                print(f"  ⚠️ Wordmark non trovato: {wordmark_image_path}")
            
            # Salva composizione
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            canvas.save(output_path, 'PNG', optimize=True)
            print(f"  💾 Front salvato: {os.path.basename(output_path)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Errore composizione front: {e}")
            return False
    
    def compose_back(self, main_image_path: str, output_path: str) -> bool:
        """
        Compone layout BACK: Solo design principale grande centrato.
        
        Args:
            main_image_path: Path design principale
            output_path: Path output PNG
            
        Returns:
            True se successo
        """
        try:
            # Canvas principale
            template = self.canvas_templates['main']
            canvas_size = (template['width'], template['height'])
            safe_margin = template['safe_margin']
            
            # Crea canvas trasparente
            canvas = Image.new('RGBA', canvas_size, (255, 255, 255, 0))
            
            print(f"🎨 Composizione BACK su canvas {canvas_size[0]}x{canvas_size[1]}px")
            
            # DESIGN PRINCIPALE (più grande per il back)
            if os.path.exists(main_image_path):
                main_img = Image.open(main_image_path).convert('RGBA')
                back_config = self.layout_config['back']['main_image']
                
                # Ridimensiona (più grande rispetto al front)
                main_resized = self.resize_maintaining_aspect(main_img, back_config, canvas_size)
                
                # Posizione centrata verticalmente
                main_pos = self.calculate_position(canvas_size, main_resized.size, back_config)
                main_pos = self.apply_safe_margins(main_pos, main_resized.size, canvas_size, safe_margin)
                
                # Componi su canvas
                canvas.paste(main_resized, main_pos, main_resized)
                print(f"  ✅ Design back: {main_resized.size} @ {main_pos}")
            else:
                print(f"  ⚠️ Design principale non trovato: {main_image_path}")
                return False
            
            # Salva composizione
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            canvas.save(output_path, 'PNG', optimize=True)
            print(f"  💾 Back salvato: {os.path.basename(output_path)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Errore composizione back: {e}")
            return False
    
    def compose_sleeve(self, logo_image_path: str, output_path: str) -> bool:
        """
        Compone layout SLEEVE: Solo logo OnlyOne centrato.
        
        Args:
            logo_image_path: Path logo OnlyOne
            output_path: Path output PNG
            
        Returns:
            True se successo
        """
        try:
            # Canvas manica 3x14" @300DPI
            template = self.canvas_templates['sleeve']
            canvas_size = (template['width'], template['height'])
            safe_margin = template['safe_margin']
            
            # Crea canvas trasparente
            canvas = Image.new('RGBA', canvas_size, (255, 255, 255, 0))
            
            print(f"🎨 Composizione SLEEVE su canvas {canvas_size[0]}x{canvas_size[1]}px")
            
            # LOGO ONLYONE
            if os.path.exists(logo_image_path):
                logo_img = Image.open(logo_image_path).convert('RGBA')
                sleeve_config = self.layout_config['sleeve']['logo']
                
                # Ridimensiona
                logo_resized = self.resize_maintaining_aspect(logo_img, sleeve_config, canvas_size)
                
                # Posizione centrata
                logo_pos = self.calculate_position(canvas_size, logo_resized.size, sleeve_config)
                logo_pos = self.apply_safe_margins(logo_pos, logo_resized.size, canvas_size, safe_margin)
                
                # Componi su canvas
                canvas.paste(logo_resized, logo_pos, logo_resized)
                print(f"  ✅ Logo sleeve: {logo_resized.size} @ {logo_pos}")
            else:
                print(f"  ⚠️ Logo non trovato: {logo_image_path}")
                return False
            
            # Salva composizione
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            canvas.save(output_path, 'PNG', optimize=True)
            print(f"  💾 Sleeve salvato: {os.path.basename(output_path)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Errore composizione sleeve: {e}")
            return False
    
    def create_all_variants_for_product(self, slug: str, main_image_path: str, 
                                       asset_urls: Dict[str, str], 
                                       output_dir: str = "artifacts") -> Dict[str, str]:
        """
        Crea tutte le varianti di composizione per un prodotto.
        
        Args:
            slug: Slug prodotto (es. "cavallo-spettrale")
            main_image_path: Path immagine principale
            asset_urls: Dict con path degli asset (title_dark, title_light, wordmark_dark, etc.)
            output_dir: Directory output
            
        Returns:
            Dict con path dei file generati
        """
        results = {
            'front_light': None,
            'front_dark': None,
            'back': None,
            'sleeve_light': None,
            'sleeve_dark': None
        }
        
        # Crea directory prodotto
        product_dir = os.path.join(output_dir, slug)
        os.makedirs(product_dir, exist_ok=True)
        
        print(f"\n🎨 COMPOSIZIONE COMPLETA: {slug}")
        print("="*50)
        
        try:
            # 1. FRONT LIGHT (per capi chiari - elementi scuri)
            if asset_urls.get('title_dark') and asset_urls.get('wordmark_dark'):
                front_light_path = os.path.join(product_dir, f"{slug}_front_light.png")
                success = self.compose_front(
                    main_image_path,
                    asset_urls['title_dark'],
                    asset_urls['wordmark_dark'],
                    front_light_path
                )
                if success:
                    results['front_light'] = front_light_path
            
            # 2. FRONT DARK (per capi scuri - elementi chiari)
            if asset_urls.get('title_light') and asset_urls.get('wordmark_light'):
                front_dark_path = os.path.join(product_dir, f"{slug}_front_dark.png")
                success = self.compose_front(
                    main_image_path,
                    asset_urls['title_light'],
                    asset_urls['wordmark_light'],
                    front_dark_path
                )
                if success:
                    results['front_dark'] = front_dark_path
            
            # 3. BACK (universale)
            back_path = os.path.join(product_dir, f"{slug}_back.png")
            success = self.compose_back(main_image_path, back_path)
            if success:
                results['back'] = back_path
            
            # 4. SLEEVE DARK (per capi chiari - logo scuro)
            if asset_urls.get('logo_dark'):
                sleeve_dark_path = os.path.join(product_dir, f"{slug}_sleeve_dark.png")
                success = self.compose_sleeve(asset_urls['logo_dark'], sleeve_dark_path)
                if success:
                    results['sleeve_dark'] = sleeve_dark_path
            
            # 5. SLEEVE LIGHT (per capi scuri - logo chiaro)
            if asset_urls.get('logo_light'):
                sleeve_light_path = os.path.join(product_dir, f"{slug}_sleeve_light.png")
                success = self.compose_sleeve(asset_urls['logo_light'], sleeve_light_path)
                if success:
                    results['sleeve_light'] = sleeve_light_path
            
            # Summary
            successful = sum(1 for path in results.values() if path is not None)
            print(f"\n📊 RISULTATI: {successful}/5 composizioni create")
            
            return results
            
        except Exception as e:
            print(f"❌ Errore creazione varianti: {e}")
            return results

def validate_composition(image_path: str, canvas_type: str = 'main') -> Dict[str, any]:
    """
    Valida composizione generata per QA.
    
    Args:
        image_path: Path immagine da validare
        canvas_type: 'main' o 'sleeve'
        
    Returns:
        Dict con risultati validazione
    """
    from config_printful import CANVAS_TEMPLATES, QA_CONFIG
    
    result = {
        'valid': True,
        'issues': [],
        'warnings': [],
        'stats': {}
    }
    
    try:
        if not os.path.exists(image_path):
            result['valid'] = False
            result['issues'].append("File non esistente")
            return result
        
        # Carica immagine
        with Image.open(image_path) as img:
            # Controlla dimensioni canvas
            expected_size = (CANVAS_TEMPLATES[canvas_type]['width'], 
                           CANVAS_TEMPLATES[canvas_type]['height'])
            
            if img.size != expected_size:
                result['issues'].append(f"Dimensioni {img.size}, attese {expected_size}")
                result['valid'] = False
            
            # Controlla trasparenza
            if img.mode != 'RGBA':
                result['warnings'].append(f"Modalità {img.mode}, consigliata RGBA")
            
            # Dimensioni file
            file_size = os.path.getsize(image_path)
            result['stats']['file_size_mb'] = file_size / (1024 * 1024)
            
            if file_size > 50 * 1024 * 1024:  # 50MB
                result['warnings'].append(f"File grande: {result['stats']['file_size_mb']:.1f}MB")
        
        print(f"🔍 Validazione {os.path.basename(image_path)}: {'✅' if result['valid'] else '❌'}")
        
    except Exception as e:
        result['valid'] = False
        result['issues'].append(f"Errore validazione: {e}")
    
    return result
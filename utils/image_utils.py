# utils/image_utils.py - Versione estesa con validazione OnlyOne
from typing import Tuple, Dict, Optional
from PIL import Image, ImageCms
import os
import numpy as np

def get_image_dimensions(image_path: str) -> Tuple[int, int]:
    """Ottiene le dimensioni reali dell'immagine in pixel"""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            print(f"📏 Dimensioni {os.path.basename(image_path)}: {width}x{height} px")
            return width, height
    except Exception as e:
        print(f"❌ Errore nel leggere le dimensioni di {image_path}: {str(e)}")
        return 0, 0

def calculate_print_file_dimensions(img_width: int, img_height: int, 
                                   print_area_width: int = 4500, 
                                   print_area_height: int = 5100, 
                                   dpi: int = 150) -> dict:
    """
    Calcola le dimensioni ottimali per Printful
    
    Printful raccomanda:
    - Minimo 150 DPI
    - Ideale 300 DPI
    - Dimensioni in pixel basate sull'area di stampa
    """
    if img_width == 0 or img_height == 0:
        return {'width': 0, 'height': 0, 'x': 0, 'y': 0}
    
    # Calcola aspect ratio
    img_aspect = img_width / img_height
    print_aspect = print_area_width / print_area_height
    
    # Ridimensiona mantenendo aspect ratio
    if img_aspect > print_aspect:
        # Immagine più larga
        new_width = print_area_width
        new_height = int(print_area_width / img_aspect)
    else:
        # Immagine più alta
        new_height = print_area_height
        new_width = int(print_area_height * img_aspect)
    
    # Centra l'immagine nell'area di stampa
    x = (print_area_width - new_width) // 2
    y = (print_area_height - new_height) // 2
    
    return {
        'width': new_width,
        'height': new_height,
        'x': x,
        'y': y,
        'dpi': dpi
    }

# ==================== ONLYONE VALIDATIONS ====================

def validate_png_transparency(image_path: str) -> Dict[str, any]:
    """
    Valida che l'immagine sia PNG con trasparenza
    
    Returns:
        Dict con risultato validazione
    """
    result = {
        'valid': False,
        'format': None,
        'has_transparency': False,
        'mode': None,
        'issues': []
    }
    
    try:
        with Image.open(image_path) as img:
            # Controlla formato
            result['format'] = img.format
            result['mode'] = img.mode
            
            if img.format != 'PNG':
                result['issues'].append(f"Formato {img.format}, richiesto PNG")
                return result
            
            # Controlla trasparenza (con auto-fix per RGB)
            if img.mode in ('RGBA', 'LA', 'P'):
                if img.mode == 'P' and 'transparency' in img.info:
                    result['has_transparency'] = True
                elif img.mode in ('RGBA', 'LA'):
                    result['has_transparency'] = True
                else:
                    result['issues'].append("PNG senza canale trasparenza")
                    return result
            elif img.mode == 'RGB':
                # Auto-fix: RGB può essere convertito a RGBA
                result['has_transparency'] = False  # Non ha trasparenza ora
                result['needs_conversion'] = True   # Ma può essere convertita
                print(f"    🔄 PNG RGB rilevato - conversione a RGBA disponibile")
            else:
                result['issues'].append(f"Modalità {img.mode} non supporta trasparenza")
                return result
            
            result['valid'] = True
            return result
            
    except Exception as e:
        result['issues'].append(f"Errore apertura file: {e}")
        return result

def validate_srgb_profile(image_path: str) -> Dict[str, any]:
    """
    Valida profilo colore sRGB
    
    Returns:
        Dict con risultato validazione
    """
    result = {
        'valid': False,
        'profile_name': None,
        'is_srgb': False,
        'issues': []
    }
    
    try:
        with Image.open(image_path) as img:
            # Controlla profilo ICC
            if 'icc_profile' in img.info:
                try:
                    profile = ImageCms.ImageCmsProfile(img.info['icc_profile'])
                    profile_name = profile.profile.profile_description
                    result['profile_name'] = profile_name
                    
                    # Controlla se è sRGB (vari nomi possibili)
                    srgb_indicators = ['sRGB', 'srgb', 'SRGB', 'IEC61966', 'Adobe RGB']
                    result['is_srgb'] = any(indicator in str(profile_name) for indicator in srgb_indicators)
                    
                    if result['is_srgb']:
                        result['valid'] = True
                    else:
                        result['issues'].append(f"Profilo {profile_name} non è sRGB")
                        
                except Exception as e:
                    result['issues'].append(f"Errore lettura profilo ICC: {e}")
            else:
                # Nessun profilo ICC - assumiamo sRGB per PNG web
                result['is_srgb'] = True
                result['valid'] = True
                result['profile_name'] = "Nessun profilo (assumendo sRGB)"
                
    except Exception as e:
        result['issues'].append(f"Errore validazione profilo: {e}")
        
    return result

def validate_dpi_or_size(image_path: str, min_dpi: int = 300, min_dimension: int = 4000) -> Dict[str, any]:
    """
    Valida DPI o dimensioni minime
    
    Returns:
        Dict con risultato validazione
    """
    result = {
        'valid': False,
        'dpi': None,
        'dimensions': (0, 0),
        'max_dimension': 0,
        'meets_dpi': False,
        'meets_size': False,
        'issues': []
    }
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            result['dimensions'] = (width, height)
            result['max_dimension'] = max(width, height)
            
            # Controlla DPI se disponibile
            dpi_info = img.info.get('dpi')
            if dpi_info:
                dpi_x, dpi_y = dpi_info
                avg_dpi = (dpi_x + dpi_y) / 2
                result['dpi'] = int(avg_dpi)
                result['meets_dpi'] = avg_dpi >= min_dpi
                
                if result['meets_dpi']:
                    result['valid'] = True
                else:
                    result['issues'].append(f"DPI {avg_dpi} < {min_dpi} richiesti")
            else:
                # Nessuna info DPI, controlla dimensioni
                result['meets_size'] = result['max_dimension'] >= min_dimension
                
                if result['meets_size']:
                    result['valid'] = True
                    result['issues'].append(f"Nessun DPI, ma dimensioni OK ({result['max_dimension']}px)")
                else:
                    result['issues'].append(f"Nessun DPI e dimensioni {result['max_dimension']}px < {min_dimension}px")
                    
    except Exception as e:
        result['issues'].append(f"Errore validazione DPI/dimensioni: {e}")
        
    return result

def clean_border_artifacts(image_path: str, border_threshold: int = 2, output_path: Optional[str] = None) -> str:
    """
    Pulisce aloni/artefatti dai bordi (1-2 pixel)
    
    Args:
        image_path: Path immagine input
        border_threshold: Pixel da pulire dai bordi
        output_path: Path output (se None, sovrascrive originale)
        
    Returns:
        Path file pulito
    """
    if output_path is None:
        output_path = image_path
    
    try:
        with Image.open(image_path) as img:
            if img.mode != 'RGBA':
                # Converti a RGBA per gestire trasparenza
                img = img.convert('RGBA')
            
            # Converti in array numpy per manipolazione pixel
            img_array = np.array(img)
            height, width = img_array.shape[:2]
            
            # Pulisci bordi settando alpha a 0 (trasparente)
            # Top e bottom
            img_array[:border_threshold, :, 3] = 0  # Top
            img_array[-border_threshold:, :, 3] = 0  # Bottom
            
            # Left e right  
            img_array[:, :border_threshold, 3] = 0  # Left
            img_array[:, -border_threshold:, 3] = 0  # Right
            
            # Converti back a PIL Image
            cleaned_img = Image.fromarray(img_array, 'RGBA')
            cleaned_img.save(output_path, 'PNG', optimize=True)
            
            print(f"🧹 Puliti {border_threshold}px dai bordi: {os.path.basename(output_path)}")
            return output_path
            
    except Exception as e:
        print(f"❌ Errore pulizia bordi {image_path}: {e}")
        return image_path

def validate_onlyone_image(image_path: str) -> Dict[str, any]:
    """
    Validazione completa OnlyOne per immagine input
    
    Returns:
        Dict con risultato validazione completa
    """
    from config_printful import IMAGE_REQUIREMENTS
    
    print(f"\n🔍 Validando {os.path.basename(image_path)}...")
    
    result = {
        'valid': True,
        'image_path': image_path,
        'issues': [],
        'warnings': [],
        'validations': {}
    }
    
    # 1. Validazione PNG trasparenza (con auto-fix)
    png_result = validate_png_transparency(image_path)
    result['validations']['png_transparency'] = png_result
    
    if not png_result['valid']:
        # Se è RGB e può essere convertito, è solo un warning
        if png_result.get('needs_conversion', False):
            result['warnings'].append("PNG RGB sarà convertito a RGBA automaticamente")
        else:
            result['valid'] = False
            result['issues'].extend(png_result['issues'])
    
    # 2. Validazione profilo sRGB
    srgb_result = validate_srgb_profile(image_path)
    result['validations']['srgb_profile'] = srgb_result
    if not srgb_result['valid']:
        result['warnings'].extend(srgb_result['issues'])  # Warning, non blocca
    
    # 3. Validazione DPI/dimensioni
    dpi_result = validate_dpi_or_size(
        image_path, 
        IMAGE_REQUIREMENTS['min_dpi'], 
        IMAGE_REQUIREMENTS['min_dimension']
    )
    result['validations']['dpi_size'] = dpi_result
    if not dpi_result['valid']:
        result['valid'] = False
        result['issues'].extend(dpi_result['issues'])
    
    # 4. Controlla dimensioni file
    try:
        file_size = os.path.getsize(image_path)
        max_size = IMAGE_REQUIREMENTS['max_file_size']
        if file_size > max_size:
            result['valid'] = False
            result['issues'].append(f"File {file_size/1024/1024:.1f}MB > {max_size/1024/1024:.1f}MB")
        else:
            result['validations']['file_size'] = {'valid': True, 'size_mb': file_size/1024/1024}
    except Exception as e:
        result['warnings'].append(f"Errore controllo dimensioni file: {e}")
    
    # Summary
    if result['valid']:
        print(f"  ✅ Validazione OK")
        if result['warnings']:
            print(f"  ⚠️ {len(result['warnings'])} warning")
    else:
        print(f"  ❌ {len(result['issues'])} errori critici")
        # Debug: mostra errori dettagliati
        for issue in result['issues']:
            print(f"    • {issue}")
        if result['warnings']:
            for warning in result['warnings']:
                print(f"    ⚠️ {warning}")
    
    return result

def prepare_image_for_printful(image_path: str, max_size: Tuple[int, int] = (4500, 5100)) -> str:
    """
    Prepara l'immagine secondo le specifiche Printful MANTENENDO LA TRASPARENZA
    
    Printful requirements:
    - PNG format preferred per trasparenza
    - Max file size: 200MB
    - Min resolution: 150 DPI
    - MANTIENE il canale alpha per PNG trasparenti
    """
    try:
        with Image.open(image_path) as img:
            print(f"🎨 Preparando {os.path.basename(image_path)} (modalità: {img.mode})")
            
            # Mantieni RGBA per PNG trasparenti
            if img.mode == 'RGBA':
                print("  🔍 PNG trasparente rilevato - mantengo trasparenza")
                # NON convertire a RGB - mantieni RGBA
                processed_img = img
                
            elif img.mode == 'P':
                # Palette mode - converti a RGBA per sicurezza
                processed_img = img.convert('RGBA')
                print("  🔄 Convertito da palette a RGBA")
                
            elif img.mode in ('LA', 'L'):
                # Grayscale
                if img.mode == 'LA':
                    processed_img = img.convert('RGBA')
                    print("  🔄 Convertito da LA a RGBA")
                else:
                    processed_img = img.convert('RGB')
                    print("  🔄 Convertito da L a RGB")
                    
            elif img.mode == 'RGB':
                # RGB già pronto
                processed_img = img
                print("  ✅ RGB già ottimale")
                
            else:
                # Altri modi - converti a RGBA per sicurezza
                processed_img = img.convert('RGBA')
                print(f"  🔄 Convertito da {img.mode} a RGBA")
            
            # Ridimensiona se troppo grande (mantenendo aspect ratio)
            if processed_img.width > max_size[0] or processed_img.height > max_size[1]:
                old_size = (processed_img.width, processed_img.height)
                processed_img.thumbnail(max_size, Image.Resampling.LANCZOS)
                print(f"  🔧 Ridimensionato da {old_size} a {processed_img.size}")
            
            # Salva mantenendo il formato appropriato
            if processed_img.mode == 'RGBA':
                # PNG per trasparenza
                output_path = image_path.replace('.jpg', '.png').replace('.jpeg', '.png')
                processed_img.save(output_path, 'PNG', optimize=True)
                print(f"  💾 Salvato come PNG trasparente: {os.path.basename(output_path)}")
            else:
                # JPG per RGB (più piccolo)
                output_path = image_path.replace('.png', '.jpg')
                processed_img.save(output_path, 'JPEG', optimize=True, quality=95)
                print(f"  💾 Salvato come JPEG: {os.path.basename(output_path)}")
            
            return output_path
            
    except Exception as e:
        print(f"❌ Errore nella preparazione immagine: {e}")
        return image_path
# processors/qa_validator.py - QA Validator intelligente per OnlyOne
from PIL import Image, ImageStat
import os
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime

class OnlyOneQAValidator:
    """
    QA Validator intelligente che si adatta al contenuto e rileva problemi
    sia in scenari statici che dinamici.
    """
    
    def __init__(self):
        from config_printful import QA_CONFIG, CANVAS_TEMPLATES
        self.qa_config = QA_CONFIG
        self.canvas_templates = CANVAS_TEMPLATES
        
    def analyze_image_characteristics(self, image_path: str) -> Dict[str, any]:
        """
        Analizza caratteristiche dell'immagine per adattamento dinamico.
        
        Args:
            image_path: Path dell'immagine da analizzare
            
        Returns:
            Dict con caratteristiche rilevate
        """
        result = {
            'path': image_path,
            'exists': False,
            'dimensions': (0, 0),
            'aspect_ratio': 0,
            'orientation': 'unknown',
            'has_transparency': False,
            'complexity': 'unknown',
            'dominant_colors': [],
            'file_size_mb': 0,
            'issues': []
        }
        
        try:
            if not os.path.exists(image_path):
                result['issues'].append("File non esistente")
                return result
            
            result['exists'] = True
            result['file_size_mb'] = os.path.getsize(image_path) / (1024 * 1024)
            
            with Image.open(image_path) as img:
                # Dimensioni e orientamento
                result['dimensions'] = img.size
                width, height = img.size
                result['aspect_ratio'] = width / height if height > 0 else 0
                
                if result['aspect_ratio'] > 1.3:
                    result['orientation'] = 'horizontal'
                elif result['aspect_ratio'] < 0.7:
                    result['orientation'] = 'vertical'
                else:
                    result['orientation'] = 'square'
                
                # Trasparenza
                result['has_transparency'] = img.mode in ('RGBA', 'LA', 'P')
                
                # Converti a RGB per analisi colori
                rgb_img = img.convert('RGB')
                
                # Complessità basata su varianza colori
                stat = ImageStat.Stat(rgb_img)
                variance = sum(stat.var) / 3  # Media varianza RGB
                if variance < 1000:
                    result['complexity'] = 'low'  # Colore flat/gradiente
                elif variance < 5000:
                    result['complexity'] = 'medium'  # Pattern semplici
                else:
                    result['complexity'] = 'high'  # Dettagli complessi
                
                # Colori dominanti (semplificato)
                result['dominant_colors'] = stat.mean  # [R, G, B] media
                
        except Exception as e:
            result['issues'].append(f"Errore analisi: {e}")
        
        return result
    
    def validate_canvas_compliance(self, image_path: str, canvas_type: str = 'main') -> Dict[str, any]:
        """
        Valida conformità alle specifiche canvas Printful.
        
        Args:
            image_path: Path immagine da validare
            canvas_type: 'main' o 'sleeve'
            
        Returns:
            Dict con risultati validazione canvas
        """
        result = {
            'valid': True,
            'canvas_type': canvas_type,
            'issues': [],
            'warnings': [],
            'suggestions': []
        }
        
        try:
            if not os.path.exists(image_path):
                result['valid'] = False
                result['issues'].append("File composizione non trovato")
                return result
            
            template = self.canvas_templates[canvas_type]
            expected_size = (template['width'], template['height'])
            safe_margin = template['safe_margin']
            
            with Image.open(image_path) as img:
                # 1. Dimensioni canvas
                if img.size != expected_size:
                    result['valid'] = False
                    result['issues'].append(f"Canvas {img.size}, atteso {expected_size}")
                
                # 2. Modalità colore
                if img.mode != 'RGBA':
                    result['warnings'].append(f"Modalità {img.mode}, consigliata RGBA per trasparenza")
                
                # 3. DPI (se disponibile nei metadati)
                dpi_info = img.info.get('dpi')
                if dpi_info:
                    avg_dpi = sum(dpi_info) / 2
                    if avg_dpi < 150:
                        result['issues'].append(f"DPI {avg_dpi} < 150 (minimo Printful)")
                    elif avg_dpi < 300:
                        result['warnings'].append(f"DPI {avg_dpi} < 300 (ideale Printful)")
                
                # 4. Dimensioni file
                file_size = os.path.getsize(image_path) / (1024 * 1024)
                if file_size > 200:  # 200MB limite Printful
                    result['issues'].append(f"File {file_size:.1f}MB > 200MB limite Printful")
                elif file_size > 50:
                    result['warnings'].append(f"File grande {file_size:.1f}MB, upload lento")
                
                # 5. Contenuto in safe area (analisi pixel)
                safe_area = self._analyze_safe_area_usage(img, safe_margin)
                if safe_area['content_outside_safe']:
                    result['warnings'].append("Contenuto rilevato vicino ai bordi")
                
        except Exception as e:
            result['valid'] = False
            result['issues'].append(f"Errore validazione canvas: {e}")
        
        return result
    
    def _analyze_safe_area_usage(self, img: Image.Image, margin: int) -> Dict[str, any]:
        """
        Analizza uso della safe area cercando contenuto vicino ai bordi.
        """
        width, height = img.size
        
        # Converti a array numpy per analisi
        if img.mode == 'RGBA':
            img_array = np.array(img)
            # Usa canale alpha per rilevare contenuto
            alpha_channel = img_array[:, :, 3]
        else:
            # Per RGB usa luminanza
            gray_img = img.convert('L')
            alpha_channel = np.array(gray_img)
        
        # Definisci aree margine
        top_margin = alpha_channel[:margin, :]
        bottom_margin = alpha_channel[-margin:, :]
        left_margin = alpha_channel[:, :margin]
        right_margin = alpha_channel[:, -margin:]
        
        # Soglia per "contenuto presente" (non trasparente)
        content_threshold = 10  # Valori alpha > 10 = contenuto
        
        result = {
            'content_outside_safe': False,
            'margin_usage': {
                'top': np.sum(top_margin > content_threshold),
                'bottom': np.sum(bottom_margin > content_threshold),
                'left': np.sum(left_margin > content_threshold),
                'right': np.sum(right_margin > content_threshold)
            }
        }
        
        # Se c'è contenuto significativo nei margini
        total_margin_content = sum(result['margin_usage'].values())
        if total_margin_content > 100:  # Soglia pixel
            result['content_outside_safe'] = True
        
        return result
    
    def validate_layout_composition(self, composition_paths: Dict[str, str], 
                                   main_image_analysis: Dict) -> Dict[str, any]:
        """
        Valida qualità layout e adattabilità per diverse orientazioni.
        
        Args:
            composition_paths: Dict con path delle composizioni (front_light, front_dark, etc.)
            main_image_analysis: Analisi dell'immagine principale
            
        Returns:
            Dict con validazione layout
        """
        result = {
            'valid': True,
            'layout_score': 0,
            'adaptability_score': 0,
            'issues': [],
            'warnings': [],
            'suggestions': []
        }
        
        try:
            # 1. Analisi orientamento vs layout
            orientation = main_image_analysis.get('orientation', 'unknown')
            aspect_ratio = main_image_analysis.get('aspect_ratio', 1.0)
            
            if orientation == 'horizontal' and aspect_ratio > 2.0:
                result['warnings'].append("Immagine molto orizzontale, potrebbe essere compressa eccessivamente")
                result['suggestions'].append("Considera layout orizzontale o crop centrale")
            
            elif orientation == 'vertical' and aspect_ratio < 0.3:
                result['warnings'].append("Immagine molto verticale, potrebbe lasciare spazi vuoti laterali")
                result['suggestions'].append("Considera ridimensionamento o elementi decorativi laterali")
            
            # 2. Validazione contrasto per ogni composizione
            contrast_results = self._validate_composition_contrast(composition_paths, main_image_analysis)
            result.update(contrast_results)
            
            # 3. Calcolo score layout
            score_factors = []
            
            # Orientamento appropriato
            if orientation in ['vertical', 'square']:
                score_factors.append(25)  # +25 per orientamento buono
            elif orientation == 'horizontal' and aspect_ratio < 1.8:
                score_factors.append(15)  # +15 per orizzontale gestibile
            else:
                score_factors.append(0)   # 0 per problematico
            
            # Complessità gestibile
            complexity = main_image_analysis.get('complexity', 'unknown')
            if complexity == 'medium':
                score_factors.append(25)  # +25 per complessità ideale
            elif complexity in ['low', 'high']:
                score_factors.append(15)  # +15 per gestibile
            else:
                score_factors.append(5)   # +5 per sconosciuto
            
            # File size ragionevole
            file_size = main_image_analysis.get('file_size_mb', 0)
            if file_size < 10:
                score_factors.append(25)  # +25 per size ottima
            elif file_size < 50:
                score_factors.append(15)  # +15 per size accettabile
            else:
                score_factors.append(5)   # +5 per size grande
            
            # Trasparenza presente
            if main_image_analysis.get('has_transparency', False):
                score_factors.append(25)  # +25 per trasparenza
            else:
                score_factors.append(10)  # +10 senza trasparenza
            
            result['layout_score'] = sum(score_factors)
            result['adaptability_score'] = min(100, result['layout_score'] + 20)  # Bonus base
            
            # Validazione finale
            if result['layout_score'] < 50:
                result['valid'] = False
                result['issues'].append(f"Layout score basso ({result['layout_score']}/100)")
            elif result['layout_score'] < 70:
                result['warnings'].append(f"Layout score medio ({result['layout_score']}/100)")
            
        except Exception as e:
            result['valid'] = False
            result['issues'].append(f"Errore validazione layout: {e}")
        
        return result
    
    def _validate_composition_contrast(self, composition_paths: Dict[str, str], 
                                     main_analysis: Dict) -> Dict[str, any]:
        """
        Valida contrasto nelle composizioni front light/dark.
        """
        result = {
            'contrast_issues': [],
            'contrast_warnings': []
        }
        
        try:
            # Analizza colori dominanti dell'immagine principale
            dominant_colors = main_analysis.get('dominant_colors', [128, 128, 128])
            avg_brightness = sum(dominant_colors) / 3  # Media RGB
            
            # Suggerimenti basati su luminosità media
            if avg_brightness < 80:  # Immagine scura
                if 'front_light' not in composition_paths:
                    result['contrast_warnings'].append("Immagine scura senza variante light per capi chiari")
            elif avg_brightness > 180:  # Immagine chiara  
                if 'front_dark' not in composition_paths:
                    result['contrast_warnings'].append("Immagine chiara senza variante dark per capi scuri")
            
            # Analisi complessità per leggibilità testo
            complexity = main_analysis.get('complexity', 'medium')
            if complexity == 'high':
                result['contrast_warnings'].append("Immagine complessa, titolo potrebbe essere poco leggibile")
                result.setdefault('suggestions', []).append("Considera sfondo semitrasparente per titolo")
                
        except Exception as e:
            result['contrast_issues'].append(f"Errore analisi contrasto: {e}")
        
        return result
    
    def run_full_qa_validation(self, product_slug: str, main_image_path: str, 
                              composition_paths: Dict[str, str]) -> Dict[str, any]:
        """
        Esegue validazione QA completa per un prodotto.
        
        Args:
            product_slug: Slug prodotto
            main_image_path: Path immagine principale
            composition_paths: Dict con path composizioni generate
            
        Returns:
            Report QA completo
        """
        print(f"\n🔍 QA VALIDATION: {product_slug}")
        print("="*40)
        
        report = {
            'product_slug': product_slug,
            'timestamp': datetime.now().isoformat(),
            'overall_valid': True,
            'overall_score': 0,
            'main_image_analysis': {},
            'canvas_validations': {},
            'layout_validation': {},
            'summary': {
                'total_issues': 0,
                'total_warnings': 0,
                'recommendations': []
            }
        }
        
        try:
            # 1. Analisi immagine principale
            print("  📊 Analizzando immagine principale...")
            main_analysis = self.analyze_image_characteristics(main_image_path)
            report['main_image_analysis'] = main_analysis
            
            if not main_analysis['exists']:
                report['overall_valid'] = False
                report['summary']['total_issues'] += len(main_analysis['issues'])
                print("    ❌ Immagine principale non trovata")
                return report
            
            print(f"    ✅ {main_analysis['dimensions'][0]}×{main_analysis['dimensions'][1]}px, "
                  f"{main_analysis['orientation']}, {main_analysis['complexity']} complexity")
            
            # 2. Validazione canvas per ogni composizione
            print("  🖼️ Validando composizioni...")
            for comp_type, comp_path in composition_paths.items():
                if comp_path and os.path.exists(comp_path):
                    canvas_type = 'sleeve' if 'sleeve' in comp_type else 'main'
                    validation = self.validate_canvas_compliance(comp_path, canvas_type)
                    report['canvas_validations'][comp_type] = validation
                    
                    if not validation['valid']:
                        report['overall_valid'] = False
                    
                    report['summary']['total_issues'] += len(validation['issues'])
                    report['summary']['total_warnings'] += len(validation['warnings'])
                    
                    status = "✅" if validation['valid'] else "❌"
                    print(f"    {status} {comp_type}: {len(validation['issues'])} issues, "
                          f"{len(validation['warnings'])} warnings")
            
            # 3. Validazione layout
            print("  📐 Validando layout composition...")
            layout_validation = self.validate_layout_composition(composition_paths, main_analysis)
            report['layout_validation'] = layout_validation
            
            if not layout_validation['valid']:
                report['overall_valid'] = False
            
            report['summary']['total_issues'] += len(layout_validation['issues'])
            report['summary']['total_warnings'] += len(layout_validation['warnings'])
            report['summary']['recommendations'].extend(layout_validation.get('suggestions', []))
            
            print(f"    📊 Layout score: {layout_validation['layout_score']}/100")
            
            # 4. Score finale
            scores = [layout_validation['layout_score']]
            for canvas_val in report['canvas_validations'].values():
                # Score canvas: 100 se valid, penalità per warnings
                canvas_score = 100 if canvas_val['valid'] else 0
                canvas_score -= len(canvas_val['warnings']) * 5  # -5 per warning
                scores.append(max(0, canvas_score))
            
            report['overall_score'] = sum(scores) / len(scores) if scores else 0
            
            # Summary finale
            print(f"\n  📋 RISULTATI QA:")
            print(f"    🎯 Score generale: {report['overall_score']:.1f}/100")
            print(f"    ❌ Issues critici: {report['summary']['total_issues']}")
            print(f"    ⚠️ Warning: {report['summary']['total_warnings']}")
            print(f"    💡 Raccomandazioni: {len(report['summary']['recommendations'])}")
            
            if report['overall_valid'] and report['overall_score'] >= 70:
                print("    ✅ QUALITÀ APPROVATA")
            elif report['overall_valid']:
                print("    ⚠️ QUALITÀ ACCETTABILE")
            else:
                print("    ❌ QUALITÀ INSUFFICIENTE")
                
        except Exception as e:
            print(f"    ❌ Errore QA validation: {e}")
            report['overall_valid'] = False
            report['summary']['total_issues'] += 1
        
        return report
    
    def save_qa_report(self, report: Dict, output_dir: str = "artifacts") -> str:
        """
        Salva report QA in formato JSON.
        
        Args:
            report: Report generato da run_full_qa_validation
            output_dir: Directory output
            
        Returns:
            Path del file report salvato
        """
        slug = report.get('product_slug', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        report_filename = f"{slug}_qa_report_{timestamp}.json"
        report_path = os.path.join(output_dir, slug, report_filename)
        
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"📄 Report QA salvato: {report_filename}")
            return report_path
            
        except Exception as e:
            print(f"❌ Errore salvataggio report: {e}")
            return None

def run_batch_qa_validation(product_data: List[Dict], save_reports: bool = True) -> Dict[str, any]:
    """
    Esegue QA validation su batch di prodotti.
    
    Args:
        product_data: Lista dicts con {slug, main_image_path, composition_paths}
        save_reports: Se salvare report individuali
        
    Returns:
        Summary report batch
    """
    qa_validator = OnlyOneQAValidator()
    
    batch_summary = {
        'total_products': len(product_data),
        'valid_products': 0,
        'failed_products': 0,
        'average_score': 0,
        'common_issues': {},
        'timestamp': datetime.now().isoformat()
    }
    
    all_scores = []
    all_issues = []
    
    print(f"\n🔍 BATCH QA VALIDATION - {len(product_data)} prodotti")
    print("="*60)
    
    for product in product_data:
        slug = product.get('slug', 'unknown')
        main_image = product.get('main_image_path')
        compositions = product.get('composition_paths', {})
        
        # Esegui QA per singolo prodotto
        report = qa_validator.run_full_qa_validation(slug, main_image, compositions)
        
        if report['overall_valid']:
            batch_summary['valid_products'] += 1
        else:
            batch_summary['failed_products'] += 1
        
        all_scores.append(report['overall_score'])
        
        # Raccogli issues comuni
        for validation in report.get('canvas_validations', {}).values():
            for issue in validation.get('issues', []):
                all_issues.append(issue)
        
        # Salva report individuale se richiesto
        if save_reports:
            qa_validator.save_qa_report(report)
    
    # Calcola metriche batch
    if all_scores:
        batch_summary['average_score'] = sum(all_scores) / len(all_scores)
    
    # Issues più comuni
    from collections import Counter
    issue_counter = Counter(all_issues)
    batch_summary['common_issues'] = dict(issue_counter.most_common(5))
    
    print(f"\n📊 BATCH SUMMARY:")
    print(f"  ✅ Prodotti validi: {batch_summary['valid_products']}/{batch_summary['total_products']}")
    print(f"  📈 Score medio: {batch_summary['average_score']:.1f}/100")
    print(f"  🔍 Issues più comuni:")
    for issue, count in batch_summary['common_issues'].items():
        print(f"    • {issue}: {count}x")
    
    return batch_summary
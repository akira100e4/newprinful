# utils/advanced_tracker.py - Sistema di tracking avanzato OnlyOne
import pandas as pd
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

class OnlyOneTracker:
    """
    Sistema di tracking avanzato per workflow OnlyOne.
    Gestisce CSV con 16 colonne per tracciamento completo prodotti.
    """
    
    def __init__(self, csv_path: Optional[str] = None):
        from config_printful import CSV_TRACKING_PATH, CSV_SCHEMA
        self.csv_path = csv_path or CSV_TRACKING_PATH
        self.schema = CSV_SCHEMA
        self.df = None
        
        # Carica CSV esistente o crea nuovo
        self._load_or_create_csv()
    
    def _load_or_create_csv(self):
        """Carica CSV esistente o crea uno nuovo con schema corretto."""
        try:
            if os.path.exists(self.csv_path):
                self.df = pd.read_csv(self.csv_path)
                print(f"📊 Caricato tracking esistente: {len(self.df)} entries")
                
                # Verifica schema e aggiungi colonne mancanti
                missing_cols = [col for col in self.schema if col not in self.df.columns]
                if missing_cols:
                    print(f"  🔧 Aggiungo colonne mancanti: {missing_cols}")
                    for col in missing_cols:
                        self.df[col] = None
            else:
                # Crea nuovo DataFrame con schema completo
                self.df = pd.DataFrame(columns=self.schema)
                print(f"📄 Creato nuovo tracking CSV con {len(self.schema)} colonne")
                
        except Exception as e:
            print(f"⚠️ Errore caricamento CSV: {e}")
            print("  Creo nuovo DataFrame vuoto")
            self.df = pd.DataFrame(columns=self.schema)
    
    def create_entry(self, slug: str, title: Optional[str] = None) -> bool:
        """
        Crea nuovo entry nel tracking per un prodotto.
        
        Args:
            slug: Slug prodotto (es. "cavallo-spettrale")
            title: Titolo formattato (es. "Cavallo Spettrale")
            
        Returns:
            True se creato con successo
        """
        try:
            # Controlla se slug già esistente
            if not self.df.empty and slug in self.df['slug'].values:
                print(f"⚠️ Entry già esistente per slug: {slug}")
                return False
            
            # Crea nuovo entry
            new_entry = {col: None for col in self.schema}
            new_entry.update({
                'slug': slug,
                'title': title or slug.replace('-', ' ').title(),
                'status': 'draft',
                'timestamp': datetime.now().isoformat()
            })
            
            # Aggiungi al DataFrame
            new_row_df = pd.DataFrame([new_entry])
            self.df = pd.concat([self.df, new_row_df], ignore_index=True)
            
            print(f"✅ Creato entry per: {slug}")
            return True
            
        except Exception as e:
            print(f"❌ Errore creazione entry {slug}: {e}")
            return False
    
    def update_asset_urls(self, slug: str, asset_urls: Dict[str, str]) -> bool:
        """
        Aggiorna URL degli asset per un prodotto.
        
        Args:
            slug: Slug prodotto
            asset_urls: Dict con URL asset (artwork_url, title_dark_url, etc.)
            
        Returns:
            True se aggiornato con successo
        """
        try:
            if self.df.empty or slug not in self.df['slug'].values:
                print(f"⚠️ Entry non trovato per slug: {slug}")
                return False
            
            # Trova row da aggiornare
            row_idx = self.df[self.df['slug'] == slug].index[0]
            
            # Aggiorna solo colonne che esistono nello schema
            updated_fields = []
            for key, url in asset_urls.items():
                if key in self.schema and url:
                    self.df.at[row_idx, key] = url
                    updated_fields.append(key)
            
            if updated_fields:
                print(f"🔗 Aggiornati URL per {slug}: {', '.join(updated_fields)}")
                return True
            else:
                print(f"⚠️ Nessun URL valido da aggiornare per {slug}")
                return False
                
        except Exception as e:
            print(f"❌ Errore aggiornamento URL {slug}: {e}")
            return False
    
    def update_composition_paths(self, slug: str, composition_paths: Dict[str, str]) -> bool:
        """
        Aggiorna path delle composizioni generate.
        
        Args:
            slug: Slug prodotto
            composition_paths: Dict con path composizioni locali
            
        Returns:
            True se aggiornato con successo
        """
        try:
            if self.df.empty or slug not in self.df['slug'].values:
                print(f"⚠️ Entry non trovato per slug: {slug}")
                return False
            
            row_idx = self.df[self.df['slug'] == slug].index[0]
            
            # Mapping path locali -> colonne URL
            path_to_url_mapping = {
                'front_light': 'front_light_url',
                'front_dark': 'front_dark_url', 
                'back': 'back_url',
                'sleeve_dark': 'sleeve_dark_url',
                'sleeve_light': 'sleeve_light_url'
            }
            
            updated_fields = []
            for path_key, url_column in path_to_url_mapping.items():
                if path_key in composition_paths and composition_paths[path_key]:
                    # Per ora salva il path locale, in futuro sarà l'URL upload
                    self.df.at[row_idx, url_column] = composition_paths[path_key]
                    updated_fields.append(url_column)
            
            if updated_fields:
                print(f"🎨 Aggiornate composizioni per {slug}: {', '.join(updated_fields)}")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Errore aggiornamento composizioni {slug}: {e}")
            return False
    
    def mark_published(self, slug: str, product_data: Dict[str, Any]) -> bool:
        """
        Marca prodotto come pubblicato e aggiorna dati Printful.
        
        Args:
            slug: Slug prodotto
            product_data: Dati prodotto da Printful (product_id, store_url, etc.)
            
        Returns:
            True se aggiornato con successo
        """
        try:
            if self.df.empty or slug not in self.df['slug'].values:
                print(f"⚠️ Entry non trovato per slug: {slug}")
                return False
            
            row_idx = self.df[self.df['slug'] == slug].index[0]
            
            # Aggiorna dati pubblicazione
            updates = {
                'product_type': product_data.get('product_type', 'tshirt'),
                'product_id': product_data.get('product_id'),
                'store_url': product_data.get('store_url'),
                'price': product_data.get('price', '35.00'),
                'colors_light': product_data.get('colors_light', 'White,Natural,Sand'),
                'colors_dark': product_data.get('colors_dark', 'Black,Charcoal,Navy'),
                'sizes': product_data.get('sizes', 'S,M,L,XL,XXL'),
                'status': 'published',
                'timestamp': datetime.now().isoformat()
            }
            
            updated_fields = []
            for key, value in updates.items():
                if key in self.schema and value is not None:
                    self.df.at[row_idx, key] = value
                    updated_fields.append(key)
            
            print(f"🚀 Prodotto pubblicato: {slug} (ID: {product_data.get('product_id')})")
            print(f"  📝 Aggiornati: {', '.join(updated_fields)}")
            return True
            
        except Exception as e:
            print(f"❌ Errore pubblicazione {slug}: {e}")
            return False
    
    def get_entry(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Ottiene entry completo per un prodotto.
        
        Args:
            slug: Slug prodotto
            
        Returns:
            Dict con dati prodotto o None se non trovato
        """
        try:
            if self.df.empty or slug not in self.df['slug'].values:
                return None
            
            row = self.df[self.df['slug'] == slug].iloc[0]
            return row.to_dict()
            
        except Exception as e:
            print(f"❌ Errore recupero entry {slug}: {e}")
            return None
    
    def get_entries_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Ottiene tutti gli entries con un certo status.
        
        Args:
            status: Status da filtrare ('draft', 'published', etc.)
            
        Returns:
            Lista di dict con entries
        """
        try:
            if self.df.empty:
                return []
            
            filtered_df = self.df[self.df['status'] == status]
            return filtered_df.to_dict('records')
            
        except Exception as e:
            print(f"❌ Errore filtro per status {status}: {e}")
            return []
    
    def save(self) -> bool:
        """
        Salva il DataFrame nel file CSV.
        
        Returns:
            True se salvato con successo
        """
        try:
            # Crea directory se non esiste
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
            
            # Salva con encoding UTF-8 per caratteri speciali
            self.df.to_csv(self.csv_path, index=False, encoding='utf-8')
            
            print(f"💾 Tracking salvato: {len(self.df)} entries in {os.path.basename(self.csv_path)}")
            return True
            
        except Exception as e:
            print(f"❌ Errore salvataggio CSV: {e}")
            return False
    
    def export_summary(self) -> Dict[str, Any]:
        """
        Genera summary statistiche del tracking.
        
        Returns:
            Dict con statistiche
        """
        if self.df.empty:
            return {'total': 0, 'by_status': {}}
        
        try:
            summary = {
                'total_entries': len(self.df),
                'by_status': self.df['status'].value_counts().to_dict(),
                'by_product_type': self.df['product_type'].value_counts().to_dict(),
                'completion_stats': {},
                'recent_activity': []
            }
            
            # Statistiche completamento
            required_fields = ['artwork_url', 'title_dark_url', 'title_light_url', 
                             'front_light_url', 'front_dark_url', 'back_url']
            
            for field in required_fields:
                if field in self.df.columns:
                    completed = self.df[field].notna().sum()
                    summary['completion_stats'][field] = f"{completed}/{len(self.df)}"
            
            # Attività recente (ultimi 5)
            if 'timestamp' in self.df.columns:
                recent = self.df.nlargest(5, 'timestamp')[['slug', 'status', 'timestamp']]
                summary['recent_activity'] = recent.to_dict('records')
            
            return summary
            
        except Exception as e:
            print(f"❌ Errore generazione summary: {e}")
            return {'error': str(e)}
    
    def print_summary(self):
        """Stampa summary formattato."""
        summary = self.export_summary()
        
        print(f"\n📊 ONLYONE TRACKING SUMMARY")
        print("="*40)
        print(f"📦 Totale entries: {summary.get('total_entries', 0)}")
        
        if 'by_status' in summary:
            print(f"\n📋 Per status:")
            for status, count in summary['by_status'].items():
                print(f"  • {status}: {count}")
        
        if 'by_product_type' in summary:
            print(f"\n👕 Per tipo prodotto:")
            for ptype, count in summary['by_product_type'].items():
                if pd.notna(ptype):  # Esclude valori None
                    print(f"  • {ptype}: {count}")
        
        if 'completion_stats' in summary:
            print(f"\n✅ Completamento asset:")
            for field, stat in summary['completion_stats'].items():
                field_name = field.replace('_url', '').replace('_', ' ').title()
                print(f"  • {field_name}: {stat}")
        
        if 'recent_activity' in summary and summary['recent_activity']:
            print(f"\n🕒 Attività recente:")
            for activity in summary['recent_activity'][:3]:
                timestamp = activity.get('timestamp', '')[:10]  # Solo data
                print(f"  • {activity.get('slug', 'N/A')} → {activity.get('status', 'N/A')} ({timestamp})")

def batch_create_entries(image_files: List[str], tracker: Optional[OnlyOneTracker] = None) -> OnlyOneTracker:
    """
    Crea entries batch per lista di immagini.
    
    Args:
        image_files: Lista path immagini
        tracker: Tracker esistente (opzionale)
        
    Returns:
        Tracker con entries create
    """
    from utils.text_utils import generate_kebab_slug, extract_title_from_slug
    
    if tracker is None:
        tracker = OnlyOneTracker()
    
    print(f"\n📝 CREAZIONE BATCH ENTRIES - {len(image_files)} immagini")
    print("="*50)
    
    created_count = 0
    
    for image_file in image_files:
        try:
            # Genera slug da nome file
            filename = os.path.basename(image_file)
            slug = generate_kebab_slug(filename)
            title = extract_title_from_slug(slug)
            
            # Crea entry se non esiste
            if tracker.create_entry(slug, title):
                created_count += 1
            
        except Exception as e:
            print(f"❌ Errore creazione entry per {image_file}: {e}")
    
    print(f"\n📊 Risultati: {created_count}/{len(image_files)} entries create")
    
    # Salva automaticamente
    tracker.save()
    
    return tracker

def update_batch_with_qa_reports(qa_reports: List[Dict], tracker: Optional[OnlyOneTracker] = None) -> OnlyOneTracker:
    """
    Aggiorna tracker con risultati QA batch.
    
    Args:
        qa_reports: Lista report QA
        tracker: Tracker esistente
        
    Returns:
        Tracker aggiornato
    """
    if tracker is None:
        tracker = OnlyOneTracker()
    
    print(f"\n📋 AGGIORNAMENTO CON QA REPORTS - {len(qa_reports)} report")
    print("="*50)
    
    for report in qa_reports:
        slug = report.get('product_slug')
        if not slug:
            continue
        
        try:
            # Aggiorna con dati QA (potrebbe essere una colonna futura)
            qa_summary = {
                'qa_score': report.get('overall_score', 0),
                'qa_status': 'passed' if report.get('overall_valid') else 'failed'
            }
            
            # Per ora salva come JSON in note future o come campo separato
            print(f"  📊 QA per {slug}: {qa_summary['qa_score']:.1f}/100 - {qa_summary['qa_status']}")
            
        except Exception as e:
            print(f"❌ Errore aggiornamento QA per {slug}: {e}")
    
    tracker.save()
    return tracker
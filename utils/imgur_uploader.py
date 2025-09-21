# utils/imgur_uploader.py - Riscrittura completa per OnlyOne workflow
import os
import base64
import requests
import time
from typing import Dict, List, Optional

class ImgurUploader:
    """
    Uploader Imgur robusto che preserva la trasparenza PNG
    """
    
    def __init__(self, client_id: str = "546c25a59c58ad7"):
        self.client_id = client_id
        self.upload_url = "https://api.imgur.com/3/upload"
        self.uploaded_images = {}
        
    def upload_image(self, image_path: str, title: Optional[str] = None) -> str:
        """
        Carica una singola immagine su Imgur.
        
        Args:
            image_path: Path dell'immagine da caricare
            title: Titolo opzionale per l'immagine
            
        Returns:
            URL pubblico dell'immagine caricata
            
        Raises:
            FileNotFoundError: Se il file non esiste
            Exception: Se l'upload fallisce
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Immagine non trovata: {image_path}")
        
        filename = os.path.basename(image_path)
        if title is None:
            title = os.path.splitext(filename)[0]
            
        print(f"📤 {filename}...", end="", flush=True)
        
        try:
            # Leggi e codifica immagine
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Prepara headers
            headers = {
                'Authorization': f'Client-ID {self.client_id}',
                'Content-Type': 'application/json',
                'User-Agent': 'OnlyOne-Uploader/1.0'
            }
            
            # Payload
            payload = {
                'image': image_data,
                'type': 'base64',
                'title': title,
                'description': 'OnlyOne Printful upload'
            }
            
            # Upload
            response = requests.post(
                self.upload_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Verifica risposta
            if not result.get('success', False):
                error_msg = result.get('data', {}).get('error', 'Upload fallito')
                print(f" ❌ {error_msg}")
                raise Exception(f"Imgur error: {error_msg}")
            
            url = result['data']['link']
            if not url:
                print(" ❌ URL vuoto")
                raise Exception("URL vuoto ricevuto da Imgur")
            
            # Salva in cache
            self.uploaded_images[image_path] = url
            print(" ✅")
            return url
            
        except requests.exceptions.Timeout:
            print(" ❌ Timeout")
            raise Exception("Timeout durante upload")
        except requests.exceptions.RequestException as e:
            print(f" ❌ Errore rete")
            raise Exception(f"Errore rete: {e}")
        except Exception as e:
            print(f" ❌ {str(e)}")
            raise
    
    def upload_multiple_images(self, image_paths: List[str]) -> Dict[str, str]:
        """
        Upload multiplo con gestione errori e rate limiting.
        
        Args:
            image_paths: Lista di path immagini
            
        Returns:
            Dict {image_path: url} per upload riusciti
        """
        if not image_paths:
            return {}
        
        print(f"📦 Upload batch: {len(image_paths)} immagini")
        
        successful_uploads = {}
        failed_uploads = []
        
        for i, image_path in enumerate(image_paths, 1):
            try:
                # Title univoco per evitare duplicati
                timestamp = int(time.time())
                title = f"onlyone_{timestamp}_{i}"
                
                url = self.upload_image(image_path, title)
                successful_uploads[image_path] = url
                
                # Rate limiting: pausa tra upload
                if i < len(image_paths):
                    time.sleep(1.5)
                    
            except Exception as e:
                failed_uploads.append((image_path, str(e)))
                print(f"❌ {os.path.basename(image_path)}: {e}")
                
                # Pausa anche sui fallimenti per evitare rate limit
                time.sleep(0.5)
        
        # Summary
        print(f"\n📊 Risultati batch:")
        print(f"  ✅ Successi: {len(successful_uploads)}")
        print(f"  ❌ Fallimenti: {len(failed_uploads)}")
        
        if failed_uploads and len(failed_uploads) <= 3:
            print("  File falliti:")
            for path, error in failed_uploads:
                print(f"    • {os.path.basename(path)}: {error}")
        elif failed_uploads:
            print(f"  File falliti: {len(failed_uploads)} (primi 3 mostrati sopra)")
        
        return successful_uploads
    
    def get_public_url(self, image_path: str) -> str:
        """
        Ottiene URL pubblico di un'immagine precedentemente caricata.
        
        Args:
            image_path: Path dell'immagine
            
        Returns:
            URL pubblico dell'immagine
            
        Raises:
            ValueError: Se l'immagine non è stata caricata
        """
        if image_path in self.uploaded_images:
            return self.uploaded_images[image_path]
        
        # Prova a caricare se non è in cache
        try:
            return self.upload_image(image_path)
        except Exception:
            raise ValueError(f"Immagine non caricata e upload fallito: {image_path}")
    
    def verify_url_accessibility(self, url: str) -> bool:
        """
        Verifica che un URL sia accessibile.
        
        Args:
            url: URL da verificare
            
        Returns:
            True se accessibile
        """
        try:
            # User-Agent simile a quello che userebbe Printful
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; Printful/1.0)',
                'Accept': 'image/*,*/*;q=0.8'
            }
            
            response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                return content_type.startswith('image/')
            
            return False
            
        except Exception:
            return False
    
    def batch_verify_urls(self) -> Dict[str, bool]:
        """
        Verifica accessibilità di tutti gli URL caricati.
        
        Returns:
            Dict {image_path: accessible} per tutte le immagini
        """
        if not self.uploaded_images:
            return {}
        
        print(f"🔍 Verifica accessibilità {len(self.uploaded_images)} URL...")
        
        results = {}
        accessible_count = 0
        
        for image_path, url in self.uploaded_images.items():
            accessible = self.verify_url_accessibility(url)
            results[image_path] = accessible
            
            if accessible:
                accessible_count += 1
            
            # Piccola pausa per essere gentili con Imgur
            time.sleep(0.2)
        
        print(f"  ✅ Accessibili: {accessible_count}/{len(self.uploaded_images)}")
        
        return results
    
    def get_all_urls(self) -> Dict[str, str]:
        """
        Ritorna copia di tutte le URL caricate.
        
        Returns:
            Dict {image_path: url}
        """
        return self.uploaded_images.copy()
    
    def clear_cache(self):
        """Pulisce la cache delle URL caricate"""
        self.uploaded_images.clear()
        print("🧹 Cache URL pulita")
    
    def get_cache_info(self) -> Dict:
        """
        Informazioni sulla cache attuale.
        
        Returns:
            Dict con statistiche cache
        """
        return {
            'total_uploads': len(self.uploaded_images),
            'images': list(self.uploaded_images.keys()),
            'client_id': f"{self.client_id[:10]}...",
            'upload_url': self.upload_url
        }

def test_imgur_connection() -> bool:
    """
    Test veloce di connettività Imgur.
    
    Returns:
        True se Imgur è raggiungibile
    """
    try:
        response = requests.get(
            "https://api.imgur.com/3/credits",
            headers={
                'Authorization': 'Client-ID 546c25a59c58ad7',
                'User-Agent': 'OnlyOne-Uploader/1.0'
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception:
        return False

def create_uploader() -> ImgurUploader:
    """
    Factory function per creare uploader con test di connessione.
    
    Returns:
        ImgurUploader configurato
        
    Raises:
        Exception: Se Imgur non è raggiungibile
    """
    if not test_imgur_connection():
        raise Exception("Imgur non raggiungibile - controlla connessione internet")
    
    return ImgurUploader()

# Alias per compatibilità con codice esistente
ImgurUploaderOld = ImgurUploader
# api/printful_api.py
import requests
import time
import json
from typing import Dict, List, Optional, Any

class PrintfulAPI:
    def __init__(self, api_key: str, store_id: str):
        """
        Inizializza il client API Printful
        
        Args:
            api_key: Token API di Printful
            store_id: ID dello store Printful
        """
        self.api_key = api_key
        self.store_id = store_id
        self.base_url = "https://api.printful.com"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-PF-Store-Id": str(store_id)
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_reset = time.time() + 60
        
    def _handle_rate_limit(self):
        """Gestisce il rate limiting di Printful (120 richieste al minuto)"""
        current_time = time.time()
        
        # Reset counter ogni minuto
        if current_time > self.rate_limit_reset:
            self.request_count = 0
            self.rate_limit_reset = current_time + 60
            
        # Se abbiamo raggiunto il limite, aspetta
        if self.request_count >= 115:  # Lasciamo un margine di sicurezza
            sleep_time = self.rate_limit_reset - current_time
            if sleep_time > 0:
                print(f"⏸️ Rate limit raggiunto, aspetto {sleep_time:.1f} secondi...")
                time.sleep(sleep_time)
                self.request_count = 0
                self.rate_limit_reset = time.time() + 60
        
        self.request_count += 1
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """
        Esegue una richiesta HTTP all'API Printful
        """
        self._handle_rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(method, url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Errore API Printful: {e}")
            if hasattr(e.response, 'text'):
                try:
                    error_data = e.response.json()
                    print(f"Dettagli errore: {error_data}")
                except:
                    print(f"Dettagli: {e.response.text}")
            raise
    
    def get_store_info(self) -> Dict:
        """Ottiene le informazioni dello store"""
        return self._make_request("GET", f"/stores/{self.store_id}")
    
    def get_product_info(self, product_id: int) -> Dict:
        """Ottiene informazioni dettagliate su un prodotto"""
        return self._make_request("GET", f"/products/{product_id}")
    
    def create_sync_product(self, product_data: Dict) -> Dict:
        """
        Crea un prodotto sincronizzato su Printful
        
        Args:
            product_data: Dati del prodotto nel formato Printful
            
        Returns:
            Risposta dell'API con i dettagli del prodotto creato
        """
        print(f"📡 Inviando dati prodotto a Printful...")
        
        # Debug: stampa la struttura dei dati (solo le chiavi principali)
        if 'sync_variants' in product_data:
            print(f"   📦 {len(product_data['sync_variants'])} varianti")
            
            # Mostra info sulla prima variante per debug
            if product_data['sync_variants']:
                first_variant = product_data['sync_variants'][0]
                files_count = len(first_variant.get('files', []))
                print(f"   🖼️ {files_count} file per variante")
        
        return self._make_request("POST", f"/store/products", data=product_data)
    
    def create_sync_variant(self, product_id: str, variant_data: Dict) -> Dict:
        """
        Aggiunge una variante a un prodotto esistente
        """
        return self._make_request("POST", f"/store/products/{product_id}/variants", data=variant_data)
    
    def publish_product(self, product_id: str) -> Dict:
        """Pubblica un prodotto"""
        data = {
            "is_ignored": False
        }
        return self._make_request("PUT", f"/store/products/{product_id}", data=data)
    
    def get_catalog_product(self, product_id: int) -> Dict:
        """Ottiene il catalogo di un prodotto specifico con tutte le varianti"""
        return self._make_request("GET", f"/products/{product_id}")
    
    def get_catalog_variants(self, product_id: int) -> List[Dict]:
        """Ottiene tutte le varianti disponibili per un prodotto"""
        response = self.get_catalog_product(product_id)
        return response.get('result', {}).get('variants', [])
    
    def get_sync_products(self, limit: int = 100) -> Dict:
        """Ottiene i prodotti sincronizzati dello store"""
        return self._make_request("GET", f"/store/products?limit={limit}")
    
    def get_sync_product(self, product_id: str) -> Dict:
        """Ottiene un prodotto sincronizzato specifico"""
        return self._make_request("GET", f"/store/products/{product_id}")
    
    def update_sync_product(self, product_id: str, product_data: Dict) -> Dict:
        """Aggiorna un prodotto sincronizzato"""
        return self._make_request("PUT", f"/store/products/{product_id}", data=product_data)
    
    def delete_sync_product(self, product_id: str) -> Dict:
        """Elimina un prodotto sincronizzato"""
        return self._make_request("DELETE", f"/store/products/{product_id}")
    
    def test_image_url(self, image_url: str) -> bool:
        """
        Testa se un URL immagine è accessibile da Printful
        
        Args:
            image_url: URL dell'immagine da testare
            
        Returns:
            True se l'URL è accessibile
        """
        try:
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                # Verifica che sia effettivamente un'immagine
                content_type = response.headers.get('content-type', '')
                if content_type.startswith('image/'):
                    return True
                else:
                    print(f"⚠️ URL non restituisce un'immagine: {content_type}")
                    return False
            else:
                print(f"⚠️ URL non accessibile: status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Errore nel testare URL {image_url}: {e}")
            return False
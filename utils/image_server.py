# utils/image_server.py - Versione Ottimizzata
import os
import threading
import time
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote
import socket

class OptimizedImageHandler(BaseHTTPRequestHandler):
    """Handler HTTP ottimizzato per servire immagini velocemente"""
    
    def do_GET(self):
        """Gestisce le richieste GET per le immagini"""
        try:
            # Decodifica l'URL
            path = unquote(self.path.lstrip('/'))
            file_path = os.path.join(self.server.image_directory, path)
            
            # Verifica sicurezza
            if not os.path.abspath(file_path).startswith(self.server.image_directory):
                self.send_error(403, "Accesso negato")
                return
            
            if not (os.path.exists(file_path) and os.path.isfile(file_path)):
                self.send_error(404, "File non trovato")
                return
            
            # Ottieni info file
            file_size = os.path.getsize(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'
            
            # Invia headers ottimizzati
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(file_size))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Cache-Control', 'public, max-age=3600')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Invia file in chunks per evitare timeout
            with open(file_path, 'rb') as f:
                chunk_size = 65536  # 64KB chunks
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    except BrokenPipeError:
                        # Client ha chiuso la connessione
                        break
                        
        except Exception as e:
            try:
                self.send_error(500, f"Errore interno: {e}")
            except:
                pass  # Connessione già chiusa
    
    def log_message(self, format, *args):
        """Log silenzioso per performance"""
        pass

class ImageServer:
    """Server HTTP veloce per servire immagini locali a Printful"""
    
    def __init__(self, image_directory: str, port: int = 8000):
        self.image_directory = os.path.abspath(image_directory)
        self.port = self._find_free_port(port)
        self.server = None
        self.server_thread = None
        self.base_url = f"http://localhost:{self.port}"
        
    def _find_free_port(self, start_port: int = 8000) -> int:
        """Trova una porta libera"""
        for port in range(start_port, start_port + 50):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(('localhost', port))
                    return port
            except OSError:
                continue
        raise RuntimeError("Nessuna porta libera trovata")
    
    def start(self):
        """Avvia il server in background"""
        if self.server is not None:
            return
        
        # Crea server ottimizzato
        self.server = HTTPServer(('localhost', self.port), OptimizedImageHandler)
        self.server.image_directory = self.image_directory
        
        # Ottimizzazioni socket
        self.server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.timeout = 30
        
        # Avvia in thread daemon
        self.server_thread = threading.Thread(
            target=self.server.serve_forever, 
            daemon=True
        )
        self.server_thread.start()
        
        # Verifica rapida
        time.sleep(0.1)
        print(f"🚀 Server HTTP veloce avviato su {self.base_url}")
        
    def stop(self):
        """Ferma il server"""
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            if self.server_thread:
                self.server_thread.join(timeout=1)
                self.server_thread = None
    
    def get_image_url(self, image_path: str) -> str:
        """Converte un path locale in URL servito dal server"""
        abs_path = os.path.abspath(image_path)
        
        if not abs_path.startswith(self.image_directory):
            filename = os.path.basename(abs_path)
            potential_path = os.path.join(self.image_directory, filename)
            if os.path.exists(potential_path):
                abs_path = potential_path
            else:
                # Cerca ricorsivamente
                for root, dirs, files in os.walk(self.image_directory):
                    if filename in files:
                        abs_path = os.path.join(root, filename)
                        break
                else:
                    raise ValueError(f"Immagine non trovata: {image_path}")
        
        relative_path = os.path.relpath(abs_path, self.image_directory)
        url_path = relative_path.replace('\\', '/')
        return f"{self.base_url}/{url_path}"
    
    def test_image_access(self, image_path: str) -> bool:
        """Testa se un'immagine è accessibile via HTTP"""
        try:
            import requests
            url = self.get_image_url(image_path)
            
            # Test veloce con timeout ridotto
            response = requests.head(url, timeout=5)  # HEAD invece di GET
            return response.status_code == 200
        except Exception:
            return False
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

# Context manager veloce
def serve_images_temporarily(image_directory: str, port: int = 8000):
    """Context manager ottimizzato per servire immagini"""
    return ImageServer(image_directory, port)
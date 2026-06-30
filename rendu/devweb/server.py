#!/usr/bin/env python3
"""
Serveur unique pour TechCorp Financial Assistant.
- Sert l'interface web (index.html) sur /
- Proxy les appels API vers Ollama (localhost:11434) sur /api/*
Avantage : tout passe par la même origine (même port), donc aucun
problème de CORS, et aucune configuration particulière à faire sur Ollama.

Lancement : python3 server.py
Puis ouvrir : http://localhost:8080
"""

import http.server
import socketserver
import urllib.request
import urllib.error

PORT = 8080
OLLAMA_URL = "http://localhost:11434"


class ProxyHandler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.proxy_to_ollama()
        else:
            self.send_error(404, "Not found")

    def do_GET(self):
        if self.path.startswith("/api/") or self.path == "/ollama-status":
            self.proxy_to_ollama()
        else:
            super().do_GET()

    def proxy_to_ollama(self):
        target_path = self.path
        if target_path == "/ollama-status":
            target_path = "/"

        target_url = OLLAMA_URL + target_path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        try:
            req = urllib.request.Request(
                target_url,
                data=body,
                method=self.command,
                headers={"Content-Type": "application/json"} if body else {},
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                self.send_response(response.status)
                # On relaie TOUS les en-têtes renvoyés par Ollama (transparence totale,
                # important pour l'audit CYBER : on ne masque rien, y compris d'éventuels
                # en-têtes custom suspects)
                hop_by_hop = {"connection", "transfer-encoding", "content-length", "keep-alive"}
                for header_name, header_value in response.headers.items():
                    if header_name.lower() not in hop_by_hop:
                        self.send_header(header_name, header_value)
                self.end_headers()
                # Relais en streaming, chunk par chunk (important pour le mode stream:true)
                while True:
                    chunk = response.read(256)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except urllib.error.URLError as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"Ollama injoignable: %s"}' % str(e).encode())

    def log_message(self, format, *args):
        # Logs plus lisibles dans le terminal
        print("[%s] %s" % (self.address_string(), format % args))


if __name__ == "__main__":
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), ProxyHandler) as httpd:
        print(f"✅ TechCorp Financial Assistant disponible sur http://localhost:{PORT}")
        print(f"   (proxy transparent vers Ollama sur {OLLAMA_URL})")
        httpd.serve_forever()

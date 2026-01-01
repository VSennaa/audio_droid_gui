import time
import socket
import subprocess
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from zeroconf import Zeroconf, ServiceBrowser

# --- Configurações ---
ADB_SERVICE_TYPE = "_adb-tls-connect._tcp.local."
SERVER_PORT = 8000  # Porta fixa para o PC conectar
CURRENT_ADB_DATA = {"status": "scanning", "ip": None, "port": None}

# --- Funções Auxiliares ---
def update_notification(title, content, priority="low"):
    subprocess.run([
        "termux-notification", "--id", "adb_service_id",
        "--title", title, "--content", content,
        "--priority", priority, "--ongoing", "--icon", "settings"
    ])

def get_local_ip():
    """Pega o IP do próprio Termux para mostrar na tela"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Desconhecido"

# --- Servidor HTTP (A API) ---
class APIMinimale(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        # Retorna os dados atuais em JSON
        self.wfile.write(json.dumps(CURRENT_ADB_DATA).encode("utf-8"))

    # Remove logs do terminal pra não poluir
    def log_message(self, format, *args):
        pass

def start_server():
    server = HTTPServer(('0.0.0.0', SERVER_PORT), APIMinimale)
    print(f"🌍 API rodando em: http://{get_local_ip()}:{SERVER_PORT}")
    server.serve_forever()

# --- Monitor ADB (mDNS) ---
class ADBObserver:
    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            port = info.port
            ipv4 = next((ip for ip in addresses if "." in ip), None)

            if ipv4:
                # Atualiza a variável global que a API lê
                CURRENT_ADB_DATA["status"] = "connected"
                CURRENT_ADB_DATA["ip"] = ipv4
                CURRENT_ADB_DATA["port"] = port

                msg = f"IP: {ipv4} | Porta: {port}"
                print(f"✅ DETECTADO: {msg}")
                update_notification("AudioDroid: Pronto", f"API: {SERVER_PORT} | ADB: {port}", "high")

    def remove_service(self, zc, type_, name):
        CURRENT_ADB_DATA["status"] = "disconnected"
        print("❌ ADB perdido")
        update_notification("AudioDroid: Aguardando...", "Ative a Depuração Wireless", "low")

# --- Main ---
if __name__ == "__main__":
    print("🚀 Iniciando AudioDroid Service (mDNS + API)...")

    # 1. Inicia o Servidor HTTP em uma thread separada (background)
    threading.Thread(target=start_server, daemon=True).start()

    # 2. Inicia o Zeroconf (Monitor)
    zeroconf = Zeroconf()
    browser = ServiceBrowser(zeroconf, ADB_SERVICE_TYPE, ADBObserver())
    update_notification("AudioDroid: Iniciando", "Subindo servidor...", "low")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        subprocess.run(["termux-notification-remove", "adb_service_id"])
        print("\n🛑 Encerrando...")

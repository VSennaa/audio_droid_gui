## AudioDroid (GUI)

AudioDroid fornece uma interface para iniciar e controlar uma instância de `scrcpy` configurada para captura de áudio (modo sem vídeo). O objetivo deste repositório é automatizar a descoberta da porta ADB dinâmica e expor controles locais para volume e atalhos globais.

### Funcionalidades (resumo técnico)

- Auto-discovery ADB: consulta um endpoint HTTP exposto no dispositivo Android para obter IP/porta ADB dinâmicos.
- Execução de `scrcpy` em modo áudio: chama `scrcpy` com parâmetros de apenas áudio (`--no-video` e flags de buffer quando aplicável).
- Controle de volume por processo: ajusta o volume do processo do `scrcpy` no host Windows sem alterar o mixer global.
- Hotkeys globais: define atalhos para pausar/resumir reprodução, válidos mesmo com a janela minimizada.
- Failover de IP: mantém histórico de IPs para alternância entre redes (por exemplo, 2.4/5 GHz).

---

## Arquitetura e fluxo

1. No Android, um agente em `Termux` (script `adb_publish.py`) observa anúncios mDNS/zeroconf do ADB Wireless e expõe um pequeno servidor HTTP (por padrão `:8000`) com um payload JSON contendo `ip` e `port` do serviço ADB.
2. No host Windows, o cliente (AudioDroid) consulta `http://<IP_DO_CELULAR>:8000` para obter a porta ADB atual.
3. O cliente estabelece conexão ADB usando o IP e porta fornecidos e inicializa `scrcpy` com parâmetros que desabilitam vídeo e habilitam saída/encaminhamento de áudio.
4. Controles de volume e atalhos interagem com o processo `scrcpy` (identificação do PID) e com o `adb shell` quando necessário.

---

## Instalação e configuração

Requisitos

- Host (Windows): `python` 3.8+ (se executar a partir do código), `scrcpy` (binários compatíveis com a versão usada).  
- Dispositivo Android: `Termux` (ou outro ambiente capaz de executar Python) e depuração ADB habilitada.

1) Preparação do Android

- Habilite a depuração ADB (USB ou Wi‑Fi) em `Opções do desenvolvedor`. Para pareamento via código (Android 11+), siga o fluxo de pareamento do Android.

2) Configuração do agente no Android (Termux)

- Instalar dependências no Termux:

```sh
pkg update -y
pkg install python termux-api -y
pip install zeroconf
```

- Exemplo de `adb_publish.py` (resumo): o agente monitora serviços zeroconf `_adb-tls-connect._tcp.local.`, extrai o endereço IPv4 e a porta, e expõe o estado via HTTP JSON em `:8000`.

- Inicializador (`iniciar.sh`): mantém o agente em execução e usa `termux-wake-lock` quando necessário.

Com o agente rodando, o host já pode consultar o endpoint para obter IP/porta ADB.

3) Execução no host (PC)

- Baixe/extraia uma versão compatível de `scrcpy`.  
- Aponte a aplicação para o diretório onde estão os binários do `scrcpy`.  
- Use a função de Auto-Connect ou forneça IP/porta manualmente para iniciar o `scrcpy` em modo áudio.

---

## Arquivo de configuração

O `config.json` (gerado automaticamente na primeira execução) contém campos principais:  
- `scrcpy` / `adb`: caminhos absolutos para os executáveis.  
- `last_ip`: último IP conectado.  
- `backup_ip`: IP anterior para failover.  
- `volume`: nível de volume salvo (0.0–1.0).

Os valores podem ser ajustados manualmente conforme necessário.

---

## Scripts e exemplos

Exemplo simplificado de `adb_publish.py` (implementação mínima de referência):

```python
import time, socket, subprocess, json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from zeroconf import Zeroconf

ADB_SERVICE_TYPE = "_adb-tls-connect._tcp.local."
SERVER_PORT = 8000
CURRENT_ADB_DATA = {"status": "scanning", "ip": None, "port": None}

class APIMinimal(BaseHTTPRequestHandler):
  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.end_headers()
    self.wfile.write(json.dumps(CURRENT_ADB_DATA).encode("utf-8"))

class ADBObserver:
  def add_service(self, zc, type_, name):
    info = zc.get_service_info(type_, name)
    if info:
      ipv4 = next((socket.inet_ntoa(a) for a in info.addresses if len(a) == 4), None)
      if ipv4:
        CURRENT_ADB_DATA.update({"status": "connected", "ip": ipv4, "port": info.port})

if __name__ == "__main__":
  threading.Thread(target=lambda: HTTPServer(("0.0.0.0", SERVER_PORT), APIMinimal).serve_forever(), daemon=True).start()
  Zeroconf().add_service_listener(ADB_SERVICE_TYPE, ADBObserver())
  try:
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    pass
```

---

## Desenvolvimento

Executar a partir do código-fonte

```sh
pip install customtkinter requests keyboard pycaw comtypes zeroconf
python main.py
```

Build (criando executável)

```sh
pyinstaller --noconsole --onefile --icon=app.ico --name="AudioDroid" main.py
```

---

## Observações e limitações

- Este projeto assume que o ambiente do dispositivo Android permite execução contínua de um agente em Termux.  
- A qualidade e latência do áudio dependem da versão do `scrcpy` e das configurações de buffer/encaminhamento.  
- A operação em redes com configurações restritivas (NAT/isolamento entre SSIDs) pode exigir ajustes manuais.

---

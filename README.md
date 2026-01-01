## AudioDroid (GUI)

**AudioDroid** é uma interface minimalista para conectar o **scrcpy** em modo **apenas áudio (playback)**.  
Ele resolve o problema de **portas dinâmicas do ADB Wireless no Android 11+** e oferece **controles nativos no Windows**.

### Principais recursos

- **Auto-Connect Inteligente**  
  Detecta automaticamente a porta ADB dinâmica consultando um servidor Python no Termux via HTTP.

- **Controle de Volume Independente**  
  Ajusta o volume apenas do processo do scrcpy, sem alterar o mixer global do Windows.

- **Global Hotkeys**  
  Pause e despause a música do celular usando a tecla de mídia do teclado ou **Ctrl + Alt + P**, mesmo com o app minimizado.

- **Histórico Inteligente (Smart Stack)**  
  Alterna automaticamente entre IPs de redes diferentes (ex: Wi-Fi 2.4 GHz / 5 GHz).

---

## Como Funciona

1. O Android executa um script Python no Termux (`adb_publish.py`) que monitora o serviço **mDNS do ADB Wireless**.  
2. O script detecta a **porta dinâmica** (que muda a cada conexão) e inicia um **mini servidor HTTP na porta 8000**.  
3. O AudioDroid (PC) consulta:  
   http://IP_DO_CELULAR:8000  
4. Ao receber o JSON com a porta correta, o AudioDroid conecta o ADB e inicia o scrcpy com flags otimizadas para áudio (`--no-video`, `--audio-buffer`).  
5. O controle de volume e os atalhos de teclado interagem diretamente com o processo do scrcpy e o ADB shell.

---

## Instalação e Uso

### 1. Preparação do Android (Obrigatório)

Antes de tudo, é necessário habilitar a depuração no seu dispositivo.

<details>
<summary><b>Mostrar instruções do Android</b></summary>

#### A. Android 11+ (Recomendado – Wireless)

1. Vá em **Configurações > Opções do Desenvolvedor**
2. Ative **Depuração por Wi-Fi**
3. Toque no texto para entrar no menu e selecione **“Parear dispositivo com código”**
4. Use a função **Parear** no AudioDroid com o **IP**, **Porta** e **Código** exibidos

#### B. Android 10 ou inferior (Cabo USB)

1. Conecte o dispositivo via **USB**
2. Execute o comando: adb tcpip 5555
3. Desconecte o cabo e use a conexão manual na porta **5555**

</details>

---

### 2. Configuração do Servidor (Termux)

Para que a função **⚡ Auto Conectar** funcione, o celular precisa informar a porta ao PC.

<details>
<summary><b>Mostrar scripts do Termux</b></summary>

#### Instalar dependências no Termux

Execute no Termux:
```sh
pkg update -y  
pkg install python termux-api -y  
pip install zeroconf
```

#### Criar o script do servidor (adb_publish.py)

Crie um arquivo chamado **adb_publish.py** com o seguinte conteúdo:
```python
import time, socket, subprocess, json, threading  
from http.server import BaseHTTPRequestHandler, HTTPServer  
from zeroconf import Zeroconf  

ADB_SERVICE_TYPE = "_adb-tls-connect._tcp.local."  
SERVER_PORT = 8000  
CURRENT_ADB_DATA = {"status": "scanning", "ip": None, "port": None}  

def update_notification(title, content):  
    subprocess.run(["termux-notification", "--id", "adb_service", "--title", title, "--content", content, "--ongoing"])  

class APIMinimale(BaseHTTPRequestHandler):  
    def do_GET(self):  
        self.send_response(200)  
        self.send_header("Content-type", "application/json")  
        self.end_headers()  
        self.wfile.write(json.dumps(CURRENT_ADB_DATA).encode("utf-8"))  

class ADBObserver:  
    def add_service(self, zc, type_, name):  
        info = zc.get_service_info(type_, name)  
        if info:  
            ipv4 = next((socket.inet_ntoa(addr) for addr in info.addresses if len(addr) == 4), None)  
            if ipv4:  
                CURRENT_ADB_DATA.update({"status": "connected", "ip": ipv4, "port": info.port})  
                update_notification("AudioDroid: Online", f"API: {SERVER_PORT} | ADB: {info.port}")  

if __name__ == "__main__":  
    threading.Thread(target=lambda: HTTPServer(("0.0.0.0", SERVER_PORT), APIMinimale).serve_forever(), daemon=True).start()  
    Zeroconf().add_service_listener(ADB_SERVICE_TYPE, ADBObserver())  
    try:  
        while True: time.sleep(1)  
    except KeyboardInterrupt:  
        subprocess.run(["termux-notification-remove", "adb_service"])  
```
#### Criar o inicializador (iniciar.sh)

Crie um arquivo chamado **iniciar.sh**:
```sh
#!/bin/bash  
termux-wake-lock  
python adb_publish.py  
termux-wake-unlock  
```
#### Executar

Dê permissão e execute:

`./iniciar.sh`

</details>

---

### 3. Executando no PC

1. Baixe o [**Scrcpy v3.3.2**](https://github.com/Genymobile/scrcpy/releases)
2. Execute o **AudioDroid.exe**
3. Aponte a pasta onde o scrcpy foi extraído
4. Digite o **IP do celular** e clique em **⚡ Auto Conectar**

---

## Configuração

O arquivo **config.json** é gerado automaticamente na raiz do executável.

Campos:

- **scrcpy / adb** – Caminhos absolutos dos executáveis  
- **last_ip** – Último IP conectado  
- **backup_ip** – IP anterior (alternância de redes)  
- **volume** – Volume salvo (0.0 a 1.0)

---

## Desenvolvimento

### Executar a partir do código fonte

1. Clone o repositório
2. Instale as dependências:

`pip install customtkinter requests keyboard pycaw comtypes`

3. Execute:

`python main.py`

---

### Build (Executável)

`pyinstaller --noconsole --onefile --icon=app.ico --name="AudioDroid" main.py`

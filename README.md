## AudioDroid (GUI)

AudioDroid fornece uma interface para iniciar e controlar uma instância de `scrcpy` configurada para captura de áudio (modo sem vídeo). O objetivo deste repositório é automatizar a descoberta da porta ADB dinâmica e expor controles locais para volume e atalhos globais.

### Funcionalidades (resumo técnico)

- Auto-discovery ADB: escuta anúncios mDNS na rede local para obter IP/porta ADB dinâmicos nativos do Android.
- Pareamento QR Code: pareamento fácil apontando a câmera do celular para a tela do PC.
- Auto-ajuste de latência: ping dinâmico para calcular e definir o buffer de áudio ideal para a rede no momento da conexão.
- Execução de `scrcpy` em modo áudio: chama `scrcpy` com parâmetros de apenas áudio (`--no-video` e flags de buffer quando aplicável).
- Controle de volume por processo: ajusta o volume do processo do `scrcpy` no host Windows sem alterar o mixer global.
- Hotkeys globais: define atalhos para pausar/resumir reprodução via MediaSession (compatível com Android 14+), válidos mesmo com a janela minimizada.
- Failover de IP: mantém histórico de IPs para alternância entre redes (por exemplo, 2.4/5 GHz).

---

## Arquitetura e fluxo

1. No PC, o cliente (AudioDroid) escuta anúncios mDNS/zeroconf do ADB Wireless (`_adb-tls-connect._tcp.local.`) na rede local.
2. O cliente detecta automaticamente o IP e a porta atualizados do dispositivo Android (que mudam a cada reinício).
3. O cliente estabelece conexão ADB usando o IP e porta encontrados e inicializa `scrcpy` com parâmetros que desabilitam vídeo e habilitam saída/encaminhamento de áudio.
4. Controles de volume e atalhos interagem com o processo `scrcpy` (identificação do PID) e com o `adb shell` quando necessário.

---

## Instalação e configuração

Requisitos

- Host (Windows): `python` 3.8+ (se executar a partir do código), `scrcpy` (binários compatíveis com a versão usada).  
- Dispositivo Android: Android 11+ com depuração por Wi-Fi (ADB Wireless) ativada.

1) Preparação do Android

- Habilite a depuração ADB (Wi‑Fi) em `Opções do desenvolvedor` -> `Depuração por Wi-Fi`.
- O pareamento inicial pode ser feito via código manual ou lendo o QR Code exibido pelo próprio aplicativo AudioDroid no PC.

2) Execução no host (PC)

- Baixe/extraia uma versão compatível de [`scrcpy`](https://github.com/Genymobile/scrcpy/releases), preferencialmente a 3.3.2, mais recentes não foram testadas.  
- Aponte a aplicação para o diretório onde estão os binários do `scrcpy`.  
- Use a função de Auto-Connect ou forneça IP/porta manualmente para iniciar o `scrcpy` em modo áudio.

---

## Arquivo de configuração

O `config.json` (gerado automaticamente na primeira execução) contém campos principais:  
- `scrcpy` / `adb`: caminhos absolutos para os executáveis.  
- `last_ip`: último IP conectado.  
- `backup_ip`: IP anterior para failover.  
- `volume`: nível de volume salvo (0.0–1.0).
- `buffer`: último valor de buffer configurado.
- `auto_buffer`: preferência de usar o cálculo automático de latência.

Os valores podem ser ajustados manualmente conforme necessário.

---


## Desenvolvimento

Executar a partir do código-fonte

```sh
pip install customtkinter requests keyboard pycaw comtypes zeroconf qrcode Pillow
python main.py
```

Build (criando executável)

```sh
pyinstaller --noconsole --onefile --icon=app.ico --name="AudioDroid" main.py
```

---

## Observações e limitações

- A qualidade e latência do áudio dependem da versão do `scrcpy` e das configurações de buffer/encaminhamento.  
- A operação em redes com configurações restritivas (NAT/isolamento entre SSIDs) pode exigir ajustes manuais.

---

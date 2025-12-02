# Python Scrcpy (GUI)

Interface minimalista para conectar `scrcpy` apenas para áudio (playback), com fallbacks  
(quick connect, set 5555 via USB, manual connect), persistência `config.json`, e controle de conexão.

## Requisitos (desenvolvimento)
- Windows 10/11 (ou Linux/macOS com adaptações)
- Python 3.8+
- `pip install -r requirements.txt` (ver detalhes abaixo)
- `scrcpy` e `adb` no `PATH` para rodar sem empacotar, disponível [aqui](https://github.com/Genymobile/scrcpy)

## Instalação (dev)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install customtkinter
# ou: pip install -r requirements.txt   (se você criar esse arquivo)

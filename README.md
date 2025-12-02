# Python Scrcpy (GUI)

Interface minimalista para conectar `scrcpy` apenas para áudio (playback), com fallbacks  
(quick connect, set 5555 via USB, manual connect), persistência `config.json`, e controle de conexão.

## Requisitos (desenvolvimento)
- Windows 10/11 (ou Linux/macOS com adaptações)
- Python 3.8+
- `pip install -r requirements.txt` (ainda n fiz e nem sei se vou fazer um dia, é só uma lib kkk)
- `scrcpy` e `adb` no `PATH` para rodar sem empacotar, disponível [aqui](https://github.com/Genymobile/scrcpy)

## Instalação (dev)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install customtkinter 

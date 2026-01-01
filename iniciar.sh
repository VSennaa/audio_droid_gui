#!/bin/bash

# 1. Impede a CPU de dormir (Wakelock)
termux-wake-lock

# 2. Roda o script Python
echo "Iniciando AudioDroid Service..."
python adb_publish.py

# 3. Quando o Python fechar (CTRL+C), solta o Wakelock
termux-wake-unlock
echo "Serviço desligado."

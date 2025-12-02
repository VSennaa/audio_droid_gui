# AudioDroid (GUI)

Interface minimalista para conectar `scrcpy` apenas para áudio (playback), com fallbacks (quick connect, set 5555 via USB, manual connect), persistência de configurações (`config.json`) e controle visual de conexão.

---

## 📱 Configuração do Android (Obrigatório)

Antes de usar o programa, você precisa preparar seu celular.

### 1. Ativar Opções do Desenvolvedor
1.  Vá em **Configurações** > **Sobre o telefone**.
2.  Procure por **Número da Versão** (ou *Número de Compilação*).
3.  Toque nele **7 vezes** seguidas até aparecer a mensagem "Você agora é um desenvolvedor!".

### 2. Configurar Depuração Sem Fio (ADB Wireless)

Existem duas formas de conectar, dependendo da sua versão do Android:

#### A. Android 11 ou superior (Recomendado - Sem cabo)
1.  Vá em **Configurações** > **Sistema** > **Opções do Desenvolvedor**.
2.  Ative a opção **Depuração por Wi-Fi** (Wireless Debugging).
3.  Toque sobre o texto "Depuração por Wi-Fi" para entrar no menu.
4.  Selecione **"Parear dispositivo com código de pareamento"**.
    * Use o IP, Porta e Código mostrados nesta tela na função **Parear** do AudioDroid.
    * *Nota: O IP e Porta para pareamento mudam a cada conexão.*

#### B. Android 10 ou inferior (Ou método fixo via USB)
Se o seu Android é antigo ou você quer usar a porta padrão `5555` sem precisar parear toda vez:
1.  Conecte o celular ao PC via **Cabo USB**.
2.  Nas Opções do Desenvolvedor, ative **Depuração USB**.
3.  Abra a pasta do `scrcpy` no terminal e digite:
    ```bash
    adb tcpip 5555
    ```
4.  Pode desconectar o cabo. Agora você pode usar a **Conexão Rápida** usando apenas o IP do celular na porta 5555.

---

## 🚀 Como usar o AudioDroid

### 1. Pré-requisitos e Instalação do Scrcpy
O AudioDroid requer os binários do scrcpy para funcionar.

1.  **Baixe o scrcpy v3.3.2**:
    Acesse o site oficial e baixe a versão **3.3.2**:
    [https://github.com/Genymobile/scrcpy/releases/tag/v3.3.2](https://github.com/Genymobile/scrcpy/releases/tag/v3.3.2)
2.  **Extração**:
    Extraia a pasta do scrcpy em um local seguro do seu computador.
    *Exemplo:* `C:\scrcpy-win64-v3.3.2`

### 2. Executando o AudioDroid
1.  Execute o arquivo [**`scycrp_aud_gui.exe`**](https://github.com/VSennaa/audio_droid_gui/releases/download/1.1/scycrp_aud_gui.exe).
2.  **Primeira Execução**: O programa pedirá para selecionar a **pasta raiz** onde você extraiu o scrcpy.
    * O sistema valida automaticamente a existência de `scrcpy.exe` e `adb.exe`.
3.  Um arquivo `config.json` será gerado para salvar o caminho e suas preferências de IP/Porta.

### 3. Interface e Controles

#### Campos
* **IP:** Endereço do dispositivo Android (Ex: `10.0.0.100`).
* **Porta:** Porta ADB (Padrão: `5555` se configurado via USB, ou aleatória se via Wireless nativo).
* **Buffer:** Latência de áudio em ms (Padrão: `200`).

#### Ações
* **Conexão Rápida:** Tenta conectar no IP/Porta definidos e abre o áudio imediatamente.
* **Parear:** Inicia o pareamento ADB (Wireless Android 11+).
  > ⚠️ **Atenção:** O pareamento via interface ainda não está totalmente concluído. Caso falhe, realize o processo manualmente via terminal (CMD/Powershell) na pasta do scrcpy:
  > ```bash
  > adb pair HOST[:PORT] [PAIRING CODE]
  > ```
* **Conexão Manual:** Permite forçar conexão em IP específico.
* **Fechar Conexão:** Desconecta o ADB e encerra o processo do scrcpy, mantendo a janela aberta.

#### Observações
* **Logs:** O status da conexão e erros aparecem no painel inferior da janela.
* **Encerramento:** Ao fechar a janela, o scrcpy é finalizado e a conexão ADB é encerrada automaticamente para economizar bateria do dispositivo.

> **Nota:** Ferramenta testada e validada no **Windows** com **scrcpy 3.3.2**.

---

## 🛠️ Desenvolvimento e Build

Caso queira rodar o código fonte ou compilar por conta própria.

### Requisitos
* Windows 10/11 (Adaptável para Linux/macOS)
* Python 3.8+
* `scrcpy` e `adb` acessíveis (no PATH ou apontados na config)

### Instalação do Ambiente

```bash
# Criação do ambiente virtual
python -m venv .venv

# Ativação
.venv\Scripts\activate

# Instalação das dependências
pip install --upgrade pip
pip install customtkinter

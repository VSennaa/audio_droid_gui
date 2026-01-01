import os
import sys
import json
import time
import signal
import threading
import subprocess
from typing import Optional, Tuple

# Bibliotecas de Terceiros
import requests
import keyboard
import customtkinter as ctk
from tkinter import filedialog, messagebox

# --- Dependências de Áudio (pycaw) ---
try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False
    print("⚠️ Biblioteca 'pycaw' não instalada. Controle de volume desativado.")

# --- Constantes ---
CONFIG_FILE = "config.json"
DEFAULT_BUFFER = 200
TERMUX_PORT = 8000

# Cores de Status
STATUS_DISCONNECTED = "#C0392B"  # Vermelho
STATUS_CONNECTING = "#D35400"    # Laranja
STATUS_CONNECTED = "#27AE60"     # Verde
STATUS_SEARCHING = "#2980B9"     # Azul


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_config(scrcpy_exe, adb_exe, last_ip="", backup_ip="", volume=1.0):
    config = {
        "scrcpy": scrcpy_exe,
        "adb": adb_exe,
        "last_ip": last_ip,
        "backup_ip": backup_ip,
        "volume": volume
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def ask_scrcpy_folder() -> Optional[Tuple[str, str]]:
    folder = filedialog.askdirectory(title="Selecione a pasta raiz do scrcpy")
    if not folder:
        return None

    scrcpy_exe, adb_exe = None, None
    for root, dirs, files in os.walk(folder):
        if "scrcpy.exe" in files:
            scrcpy_exe = os.path.join(root, "scrcpy.exe")
        if "adb.exe" in files:
            adb_exe = os.path.join(root, "adb.exe")
        if scrcpy_exe and adb_exe:
            break

    if not scrcpy_exe or not adb_exe:
        messagebox.showerror("Erro", "Arquivos 'scrcpy.exe' e 'adb.exe' não encontrados.")
        return None

    save_config(scrcpy_exe, adb_exe)
    return scrcpy_exe, adb_exe


def get_subprocess_flags():
    return subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def run_adb_command(adb_path, args, log_callback=None):
    try:
        result = subprocess.run(
            [adb_path] + args,
            capture_output=True,
            text=True,
            creationflags=get_subprocess_flags()
        )
        return result.returncode == 0
    except Exception as e:
        if log_callback:
            log_callback(f"Erro ADB: {e}")
        return False


class VolumeController:
    @staticmethod
    def set_scrcpy_volume(volume_float):
        if not PYCAW_AVAILABLE:
            return
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and session.Process.name() == "scrcpy.exe":
                    volume = session.SimpleAudioVolume
                    volume.SetMasterVolume(volume_float, None)
        except Exception:
            pass


class AudioDroidApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.title("AudioDroid")

        # Tamanho Compacto Inicial
        self.geometry("600x260")
        self.resizable(False, False)

        # Carregamento de Configurações
        self.config_data = load_config()
        if not self.config_data.get("scrcpy"):
            res = ask_scrcpy_folder()
            if not res:
                self.destroy()
                return
            scrcpy_exe, adb_exe = res
            self.config_data = {"scrcpy": scrcpy_exe, "adb": adb_exe, "last_ip": "", "backup_ip": "", "volume": 1.0}

        self.scrcpy_path = self.config_data["scrcpy"]
        self.adb_path = self.config_data["adb"]

        # Variáveis de Estado
        self.ip_var = ctk.StringVar(value=self.config_data.get("last_ip", ""))
        self.port_var = ctk.StringVar(value="")
        self.buffer_var = ctk.IntVar(value=DEFAULT_BUFFER)
        
        # Carrega o volume salvo ou 1.0 (100%) por padrão
        saved_vol = self.config_data.get("volume", 1.0)
        self.volume_var = ctk.DoubleVar(value=saved_vol)
        
        self.is_log_visible = False

        self.create_widgets()
        self.setup_global_hotkeys()

        # Garante fechamento limpo ao receber CTRL+C no terminal
        signal.signal(signal.SIGINT, lambda s, f: self.close_app())

    def create_widgets(self):
        # 1. Top Bar
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkEntry(top_frame, textvariable=self.ip_var, width=120, placeholder_text="IP").pack(side="left", padx=2)
        ctk.CTkEntry(top_frame, textvariable=self.port_var, width=70, placeholder_text="Porta").pack(side="left", padx=2)
        ctk.CTkEntry(top_frame, textvariable=self.buffer_var, width=50).pack(side="left", padx=2)

        ctk.CTkButton(top_frame, text="🔗", width=30, fg_color="#555", command=self.manual_connect).pack(side="right", padx=2)
        ctk.CTkButton(top_frame, text="🔑", width=30, fg_color="#555", command=self.pair_adb_dialog).pack(side="right", padx=2)

        # 2. Status Bar
        self.status_bar = ctk.CTkLabel(
            self, text="Desconectado", fg_color=STATUS_DISCONNECTED,
            text_color="white", corner_radius=6, height=30
        )
        self.status_bar.pack(fill="x", padx=10, pady=5)

        # 3. Controles Principais
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=10, pady=5)

        self.btn_connect = ctk.CTkButton(
            ctrl_frame, text="⚡ Auto Conectar",
            fg_color="#2CC985", text_color="black", hover_color="#209160",
            command=self.thread_auto_connect, height=40
        )
        self.btn_connect.pack(fill="x", pady=(0, 10))

        # Slider e Play
        vol_frame = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        vol_frame.pack(fill="x")

        ctk.CTkLabel(vol_frame, text="🔊").pack(side="left")
        ctk.CTkSlider(vol_frame, from_=0, to=1, variable=self.volume_var, command=self.on_volume_change).pack(side="left", expand=True, padx=10)

        ctk.CTkButton(vol_frame, text="⏯", width=40, fg_color="#E0A800", text_color="black",
                      command=self.send_play_pause).pack(side="right")

        # 4. Rodapé
        footer_frame = ctk.CTkFrame(self, height=30, fg_color="transparent")
        footer_frame.pack(fill="x", side="bottom", padx=10, pady=5)

        self.btn_toggle_log = ctk.CTkButton(
            footer_frame, text="📜 Mostrar Log", width=100,
            fg_color="transparent", border_width=1, text_color="#aaa",
            command=self.toggle_log
        )
        self.btn_toggle_log.pack(side="left")

        ctk.CTkButton(footer_frame, text="Encerrar", width=80, fg_color="#922B21",
                      command=self.close_app).pack(side="right")

        # 5. Container do Log
        self.log_frame = ctk.CTkFrame(self)
        self.log_text = ctk.CTkTextbox(self.log_frame, height=150)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def setup_global_hotkeys(self):
        try:
            keyboard.add_hotkey('ctrl+alt+p', self.send_play_pause)
            self.log_print("⌨️ Atalhos Globais ativados (Ctrl+Alt+P).")
        except Exception as e:
            self.log_print(f"Erro ao registrar hotkeys (Execute como Admin): {e}")

    # --- Lógica de UI ---
    def set_status(self, text, color):
        self.status_bar.configure(text=text, fg_color=color)
        self.status_bar.update()

    def toggle_log(self):
        if self.is_log_visible:
            self.log_frame.pack_forget()
            self.geometry(f"{self.winfo_width()}x260")
            self.btn_toggle_log.configure(text="📜 Mostrar Log")
            self.is_log_visible = False
        else:
            self.geometry(f"{self.winfo_width()}x450")
            self.log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10), before=self.status_bar)
            self.log_frame.pack(fill="both", expand=True, padx=10, pady=5)
            self.btn_toggle_log.configure(text="🔼 Ocultar Log")
            self.is_log_visible = True

    def log_print(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(ctk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(ctk.END)

    # --- Lógica Principal ---
    def send_play_pause(self):
        threading.Thread(target=self._send_media_key, daemon=True).start()

    def _send_media_key(self):
        run_adb_command(self.adb_path, ["shell", "input", "keyevent", "85"], self.log_print)

    def on_volume_change(self, value):
        VolumeController.set_scrcpy_volume(value)

    def save_current_state(self):
        """Salva IPs e Volume atuais"""
        save_config(
            self.scrcpy_path,
            self.adb_path,
            self.config_data.get("last_ip", ""),
            self.config_data.get("backup_ip", ""),
            self.volume_var.get()
        )

    def update_config_ips(self, success_ip):
        """Gerencia o histórico de IPs e salva volume"""
        current_last = self.config_data.get("last_ip", "")
        current_backup = self.config_data.get("backup_ip", "")

        new_last, new_backup = current_last, current_backup

        if success_ip != current_last:
            if success_ip == current_backup:
                new_last, new_backup = success_ip, current_last
            else:
                new_last, new_backup = success_ip, current_last

        self.config_data["last_ip"] = new_last
        self.config_data["backup_ip"] = new_backup
        
        # Salva tudo, incluindo o volume atual
        self.save_current_state()

    def thread_auto_connect(self):
        threading.Thread(target=self.auto_connect_logic, daemon=True).start()

    def try_connect_termux(self, ip_target) -> Optional[int]:
        if not ip_target:
            return None
        try:
            url = f"http://{ip_target}:{TERMUX_PORT}"
            response = requests.get(url, timeout=1.5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "connected":
                    return data.get("port")
        except Exception:
            pass
        return None

    def auto_connect_logic(self):
        self.set_status("Buscando IPs...", STATUS_SEARCHING)
        manual_ip = self.ip_var.get().strip()
        last_ip = self.config_data.get("last_ip", "")
        backup_ip = self.config_data.get("backup_ip", "")

        candidates = []
        if manual_ip:
            candidates.append(manual_ip)
        if last_ip and last_ip != manual_ip:
            candidates.append(last_ip)
        if backup_ip and backup_ip != manual_ip and backup_ip != last_ip:
            candidates.append(backup_ip)

        found_port = None
        working_ip = None

        for ip in candidates:
            self.set_status(f"Testando {ip}...", STATUS_CONNECTING)
            port = self.try_connect_termux(ip)
            if port:
                found_port = port
                working_ip = ip
                break

        if found_port:
            self.port_var.set(str(found_port))
            self.ip_var.set(working_ip)
            self.update_config_ips(working_ip)
            self.connect_and_start(working_ip, str(found_port))
        else:
            self.set_status("Falha. Tente Manual.", STATUS_DISCONNECTED)
            self.log_print("Nenhum IP respondeu.")

    def pair_adb_dialog(self):
        host_port = ctk.CTkInputDialog(text="IP:Porta", title="Parear").get_input()
        if not host_port:
            return
        code = ctk.CTkInputDialog(text="Código:", title="Parear").get_input()
        if not code:
            return
        run_adb_command(self.adb_path, ["pair", host_port, code], self.log_print)

    def manual_connect(self):
        ip = self.ip_var.get()
        port = self.port_var.get()
        if not ip or not port:
            return
        self.update_config_ips(ip)
        self.connect_and_start(ip, port)

    def connect_and_start(self, ip, port):
        self.set_status(f"Conectado: {ip}:{port}", STATUS_CONNECTED)
        run_adb_command(self.adb_path, ["connect", f"{ip}:{port}"], self.log_print)
        self.start_scrcpy_process(ip, port)

    def start_scrcpy_process(self, ip, port):
        cmd = [
            self.scrcpy_path,
            "--no-window",
            "--no-video",
            "--audio-source=playback",
            f"--audio-buffer={self.buffer_var.get()}",
            "--audio-bit-rate=128K",
            f"--tcpip={ip}:{port}"
        ]
        self.log_print("Iniciando Audio...")
        try:
            subprocess.Popen(cmd, creationflags=get_subprocess_flags())
            threading.Thread(target=self.apply_initial_volume, daemon=True).start()
        except Exception as e:
            self.log_print(f"Erro scrcpy: {e}")

    def apply_initial_volume(self):
        # Aguarda scrcpy carregar e aplica o volume salvo/atual
        time.sleep(2)
        VolumeController.set_scrcpy_volume(self.volume_var.get())

    def close_app(self):
        # Salva o estado atual (Volume + IPs) antes de fechar
        self.save_current_state()
        
        try:
            run_adb_command(self.adb_path, ["disconnect"])
        except Exception:
            pass
        self.destroy()
        sys.exit(0)


if __name__ == "__main__":
    app = AudioDroidApp()
    app.mainloop()

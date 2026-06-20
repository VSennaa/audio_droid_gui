import os
import sys
import json
import time
import signal
import threading
import subprocess
from typing import Optional, Tuple
import string
import secrets
from random import randint

try:
    import qrcode
    from PIL import Image, ImageTk
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

try:
    from zeroconf import Zeroconf, ServiceBrowser, ServiceListener, IPVersion
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False

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


def save_config(scrcpy_exe, adb_exe, last_ip="", backup_ip="", volume=1.0, buffer=DEFAULT_BUFFER, auto_buffer=True):
    config = {
        "scrcpy": scrcpy_exe,
        "adb": adb_exe,
        "last_ip": last_ip,
        "backup_ip": backup_ip,
        "volume": volume,
        "buffer": buffer,
        "auto_buffer": auto_buffer
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
        if log_callback:
            output = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            if output:
                log_callback(f"ADB: {output}")
            if err:
                log_callback(f"ADB: {err}")
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


class QRADBListener(ServiceListener):
    def __init__(self, target_name, password, success_callback, log_callback, adb_path):
        self.target_name = target_name
        self.password = password
        self.success_callback = success_callback
        self.log_callback = log_callback
        self.adb_path = adb_path

    def remove_service(self, zc, type_, name):
        pass

    def add_service(self, zc, type_, name):
        if self.target_name in name:
            info = zc.get_service_info(type_, name)
            if info:
                self.pair(info)

    def update_service(self, zc, type_, name):
        pass

    def pair(self, info):
        try:
            ip_address = info.ip_addresses_by_version(IPVersion.All)[0].exploded
            port = info.port
            host_port = f"{ip_address}:{port}"
            self.log_callback(f"Serviço mDNS encontrado: {host_port}. Tentando parear...")
            success = run_adb_command(self.adb_path, ["pair", host_port, str(self.password)], self.log_callback)
            if success:
                self.log_callback("Pareamento QR bem-sucedido!")
                self.success_callback(ip_address)
            else:
                self.log_callback("Falha no pareamento QR.")
        except Exception as e:
            self.log_callback(f"Erro no listener mDNS: {e}")


class QRPairingDialog(ctk.CTkToplevel):
    def __init__(self, parent, adb_path, log_callback):
        super().__init__(parent)
        self.title("Pareamento")
        self.geometry("400x500")
        self.resizable(False, False)
        self.adb_path = adb_path
        self.log_callback = log_callback
        
        self.zeroconf = None
        self.browser = None

        # Gerar credenciais
        self.service_name = f"audiodroid-{''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))}"
        self.password = f"{randint(100000, 999999)}"
        
        self.create_widgets()
        if ZEROCONF_AVAILABLE:
            self.start_mdns()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        tab_qr = self.tabview.add("QR Code")
        tab_manual = self.tabview.add("Manual")
        
        # --- TAB QR ---
        lbl_info = ctk.CTkLabel(tab_qr, text="1. Habilite 'Depuração sem Fio'\n2. Escolha 'Parear dispositivo com QR Code'\n3. Escaneie o código abaixo:", justify="center")
        lbl_info.pack(pady=10)
        
        self.qr_label = ctk.CTkLabel(tab_qr, text="")
        self.qr_label.pack(pady=10)
        
        if QR_AVAILABLE:
            qr_data = f"WIFI:T:ADB;S:{self.service_name};P:{self.password};;"
            qr = qrcode.QRCode(box_size=6, border=2)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white").get_image()
            self.qr_image = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 200))
            self.qr_label.configure(image=self.qr_image, text="")
        else:
            self.qr_label.configure(text="Bibliotecas qrcode/Pillow não instaladas.\nInstale com: pip install qrcode Pillow")
            
        self.lbl_status = ctk.CTkLabel(tab_qr, text="Status: Aguardando scan...", text_color="#E0A800")
        self.lbl_status.pack(pady=10)
        
        # --- TAB MANUAL ---
        ctk.CTkLabel(tab_manual, text="IP:Porta (Pareamento)").pack(pady=(20, 5))
        self.entry_host = ctk.CTkEntry(tab_manual, placeholder_text="Ex: 192.168.1.10:45678")
        self.entry_host.pack(pady=5)
        
        ctk.CTkLabel(tab_manual, text="Código de Pareamento").pack(pady=(10, 5))
        self.entry_code = ctk.CTkEntry(tab_manual, placeholder_text="Ex: 123456")
        self.entry_code.pack(pady=5)
        
        btn_pair = ctk.CTkButton(tab_manual, text="Parear", command=self.do_manual_pair)
        btn_pair.pack(pady=20)

    def start_mdns(self):
        try:
            self.zeroconf = Zeroconf()
            listener = QRADBListener(
                self.service_name, 
                self.password, 
                self.on_success, 
                self.log_callback, 
                self.adb_path
            )
            self.browser = ServiceBrowser(self.zeroconf, "_adb-tls-pairing._tcp.local.", listener)
            self.log_callback("Aguardando dispositivo escanear QR Code...")
        except Exception as e:
            self.log_callback(f"Erro ao iniciar mDNS para pareamento: {e}")

    def do_manual_pair(self):
        host = self.entry_host.get()
        code = self.entry_code.get()
        if host and code:
            self.log_callback(f"Tentando pareamento manual com {host}...")
            success = run_adb_command(self.adb_path, ["pair", host, code], self.log_callback)
            if success:
                self.on_success(host.split(':')[0])
            else:
                self.log_callback("Falha no pareamento manual.")

    def on_success(self, ip_address):
        self.lbl_status.configure(text="Sucesso! Pareado.", text_color="#27AE60")
        self.log_callback(f"Pareado com {ip_address}")
        self.after(2000, self.on_close)
        
    def on_close(self):
        if self.zeroconf:
            try:
                self.zeroconf.close()
            except Exception:
                pass
        self.destroy()


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
        self.buffer_var = ctk.IntVar(value=self.config_data.get("buffer", DEFAULT_BUFFER))
        self.auto_buffer_var = ctk.BooleanVar(value=self.config_data.get("auto_buffer", True))
        
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
        self.entry_buffer = ctk.CTkEntry(top_frame, textvariable=self.buffer_var, width=50)
        self.entry_buffer.pack(side="left", padx=2)
        
        self.chk_auto_buffer = ctk.CTkCheckBox(
            top_frame, text="Auto", variable=self.auto_buffer_var, 
            command=self.toggle_auto_buffer, width=50
        )
        self.chk_auto_buffer.pack(side="left", padx=2)

        ctk.CTkButton(top_frame, text="🔗", width=30, fg_color="#555", command=self.manual_connect).pack(side="right", padx=2)
        ctk.CTkButton(top_frame, text="🔑", width=30, fg_color="#555", command=self.pair_adb_dialog).pack(side="right", padx=2)
        
        self.toggle_auto_buffer()

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
        run_adb_command(self.adb_path, ["shell", "cmd", "media_session", "dispatch", "play-pause"], self.log_print)

    def on_volume_change(self, value):
        VolumeController.set_scrcpy_volume(value)

    def toggle_auto_buffer(self):
        if self.auto_buffer_var.get():
            self.entry_buffer.configure(state="disabled")
        else:
            self.entry_buffer.configure(state="normal")

    def measure_network_latency(self, ip, port) -> int:
        latencies = []
        import time
        import socket
        for _ in range(3):
            try:
                start = time.time()
                s = socket.create_connection((ip, int(port)), timeout=0.5)
                s.close()
                latencies.append((time.time() - start) * 1000)
            except:
                pass
        if latencies:
            return int(sum(latencies) / len(latencies))
        return 100

    def save_current_state(self):
        """Salva IPs e Volume atuais"""
        save_config(
            self.scrcpy_path,
            self.adb_path,
            self.config_data.get("last_ip", ""),
            self.config_data.get("backup_ip", ""),
            self.volume_var.get(),
            self.buffer_var.get(),
            self.auto_buffer_var.get()
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

    def auto_connect_logic(self):
        self.set_status("Buscando rede...", STATUS_SEARCHING)
        
        found = {"ip": None, "port": None}
        
        class ConnectListener(ServiceListener):
            def remove_service(self, zc, type_, name):
                pass
            def add_service(self, zc, type_, name):
                info = zc.get_service_info(type_, name)
                if info:
                    try:
                        ip = info.ip_addresses_by_version(IPVersion.All)[0].exploded
                        found["ip"] = ip
                        found["port"] = info.port
                    except:
                        pass
            def update_service(self, zc, type_, name):
                pass

        if ZEROCONF_AVAILABLE:
            try:
                zc = Zeroconf()
                listener = ConnectListener()
                browser = ServiceBrowser(zc, "_adb-tls-connect._tcp.local.", listener)
                
                # Aguarda até 5 segundos
                for _ in range(50):
                    if found["ip"]:
                        break
                    time.sleep(0.1)
                    
                zc.close()
            except Exception as e:
                self.log_print(f"Erro no mDNS: {e}")
                
        if found["ip"] and found["port"]:
            self.port_var.set(str(found["port"]))
            self.ip_var.set(found["ip"])
            self.update_config_ips(found["ip"])
            self.connect_and_start(found["ip"], str(found["port"]))
        else:
            self.set_status("Nenhum celular encontrado.", STATUS_DISCONNECTED)
            self.log_print("Falha ao encontrar dispositivo via mDNS. Verifique se a depuração por Wi-Fi está ativada e conectada na mesma rede.")

    def pair_adb_dialog(self):
        dialog = QRPairingDialog(self, self.adb_path, self.log_print)
        dialog.grab_set()

    def manual_connect(self):
        ip = self.ip_var.get()
        port = self.port_var.get()
        if not ip or not port:
            return
        self.update_config_ips(ip)
        self.connect_and_start(ip, port)

    def connect_and_start(self, ip, port):
        if self.auto_buffer_var.get():
            latency = self.measure_network_latency(ip, port)
            new_buffer = latency + 30
            self.buffer_var.set(new_buffer)
            self.log_print(f"Auto Buffer: Ping {latency}ms -> Buffer {new_buffer}ms")
            self.save_current_state()

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

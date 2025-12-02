# scrcpy_audio_gui_modern.py
# requer: pip install customtkinter

import os
import json
import shutil
import signal
import subprocess
import threading
import sys
import customtkinter as ctk

CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"ip": "", "port": "", "buffer": "200"}
    try:
        with open(CONFIG_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    except:
        return {"ip": "", "port": "", "buffer": "200"}

def save_config(ip, port, buffer_ms):
    try:
        with open(CONFIG_FILE, "w", encoding="utf8") as f:
            json.dump({"ip": ip, "port": port, "buffer": buffer_ms}, f, indent=4)
    except Exception:
        pass

def find_binary(name):
    return shutil.which(name)

def run_adb(args, capture=True):
    adb_cmd = "adb"
    try:
        if capture:
            res = subprocess.run([adb_cmd] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=False)
            return res.returncode, res.stdout.strip()
        else:
            res = subprocess.run([adb_cmd] + args, shell=False)
            return res.returncode, ""
    except FileNotFoundError:
        return 127, f"adb não encontrado"
    except Exception as e:
        return 1, str(e)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")  # "dark" or "light"
        ctk.set_default_color_theme("blue")
        self.title("sa — scrcpy audio")
        self.geometry("620x420")
        self.minsize(520, 360)

        self.config = load_config()
        self.adb_path = find_binary("adb")
        self.scrcpy_path = find_binary("scrcpy")
        self.scrcpy_proc = None

        # Top frame (inputs)
        top = ctk.CTkFrame(self, corner_radius=8)
        top.pack(fill="x", padx=12, pady=(12,8))

        self.ip_var = ctk.StringVar(value=self.config.get("ip",""))
        self.port_var = ctk.StringVar(value=self.config.get("port",""))
        self.buffer_var = ctk.StringVar(value=self.config.get("buffer","200"))

        ctk.CTkLabel(top, text="IP").grid(row=0, column=0, padx=8, pady=12, sticky="w")
        self.ip_entry = ctk.CTkEntry(top, textvariable=self.ip_var, width=180)
        self.ip_entry.grid(row=0, column=1, padx=(0,12), sticky="w")

        ctk.CTkLabel(top, text="Porta").grid(row=0, column=2, padx=8, pady=12, sticky="w")
        self.port_entry = ctk.CTkEntry(top, textvariable=self.port_var, width=100)
        self.port_entry.grid(row=0, column=3, padx=(0,12), sticky="w")

        ctk.CTkLabel(top, text="Audio buffer (ms)").grid(row=0, column=4, padx=8, pady=12, sticky="w")
        self.buffer_entry = ctk.CTkEntry(top, textvariable=self.buffer_var, width=100)
        self.buffer_entry.grid(row=0, column=5, padx=(0,12), sticky="w")

        # Buttons frame
        btnf = ctk.CTkFrame(self, corner_radius=8)
        btnf.pack(fill="x", padx=12, pady=(0,8))

        self.quick_btn = ctk.CTkButton(btnf, text="Quick Connect (porta=5555)", font=ctk.CTkFont(size=10) , command=self.quick_connect)
        self.quick_btn.grid(row=0, column=0, padx=8, pady=10, sticky="ew")

        self.set_btn = ctk.CTkButton(btnf, text="Set 5555 via USB", command=self.set_5555_usb)
        self.set_btn.grid(row=0, column=1, padx=8, pady=10, sticky="ew")

        self.manual_btn = ctk.CTkButton(btnf, text="Manual Connect", command=self.manual_connect)
        self.manual_btn.grid(row=0, column=2, padx=8, pady=10, sticky="ew")

        self.disconnect_btn = ctk.CTkButton(btnf, text="Desconectar", fg_color="#b22222", hover_color="#ff3b3b", command=self.disconnect)
        self.disconnect_btn.grid(row=0, column=3, padx=8, pady=10, sticky="ew")

        btnf.grid_columnconfigure((0,1,2,3), weight=1)

        # Log area (monospace, scrollable)
        logf = ctk.CTkFrame(self, corner_radius=8)
        logf.pack(fill="both", expand=True, padx=12, pady=(0,12))

        ctk.CTkLabel(logf, text=f"adb: {self.adb_path or 'não encontrado'}  |  scrcpy: {self.scrcpy_path or 'não encontrado'}").pack(anchor="w", padx=8, pady=(8,0))

        # Use a Text widget inside a CTkFrame for monospace logs
        self.log_text = ctk.CTkTextbox(logf, width=1, height=1, wrap="none", font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8, side="left")
        scrollbar = ctk.CTkScrollbar(logf, orientation="vertical", command=self._on_scrollbar)
        scrollbar.pack(side="right", fill="y", padx=(0,8), pady=8)
        self.log_scrollbar = scrollbar

        # Bind close and SIGINT
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
        except Exception:
            pass

        # ensure log starts with a message
        self.log("Pronto. Use Quick / Manual / Set 5555.")

    def _on_scrollbar(self, *args):
        self.log_text.yview(*args)

    def log(self, text):
        # thread-safe append
        def _append():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"{text}\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _append)

    def disable_buttons(self):
        self.quick_btn.configure(state="disabled")
        self.set_btn.configure(state="disabled")
        self.manual_btn.configure(state="disabled")
        self.disconnect_btn.configure(state="disabled")

    def enable_buttons(self):
        self.quick_btn.configure(state="normal")
        self.set_btn.configure(state="normal")
        self.manual_btn.configure(state="normal")
        self.disconnect_btn.configure(state="normal")

    def quick_connect(self):
        ip = self.ip_var.get().strip()
        if not ip:
            self.log("IP vazio.")
            return
        port = "5555"
        save_config(ip, port, self.buffer_var.get().strip())
        self.log(f"Tentando quick connect em {ip}:5555 ...")
        threading.Thread(target=self._connect_and_start, args=(ip, port), daemon=True).start()

    def set_5555_usb(self):
        def job():
            self.disable_buttons()
            code, out = run_adb(["tcpip", "5555"])
            if code == 0:
                self.log("OK: porta 5555 setada via USB. Desconecte o cabo e use Quick/Manual.")
            else:
                self.log(f"Erro ao setar porta via USB: ({code}) {out}")
            self.enable_buttons()
        threading.Thread(target=job, daemon=True).start()

    def manual_connect(self):
        ip = self.ip_var.get().strip()
        port = self.port_var.get().strip()
        if not ip or not port:
            self.log("IP ou porta vazios.")
            return
        save_config(ip, port, self.buffer_var.get().strip())
        self.log(f"Tentando conectar manualmente em {ip}:{port} ...")
        threading.Thread(target=self._connect_and_start, args=(ip, port), daemon=True).start()

    def _connect_and_start(self, ip, port):
        self.disable_buttons()
        code, out = run_adb(["connect", f"{ip}:{port}"])
        self.log(f"[adb connect] retorno={code}. {out or ''}")
        if code == 0 and (("connected" in (out or "").lower()) or ("already" in (out or "").lower())):
            self.log("Conectado via adb → iniciando scrcpy (áudio)...")
            self._start_scrcpy_proc(ip, port)
        else:
            self.log("Falha ao conectar via adb. Verifique IP/Porta ou pareie o dispositivo.")
        self.enable_buttons()

    def _start_scrcpy_proc(self, ip, port):
        exe = self.scrcpy_path or find_binary("scrcpy")
        if not exe:
            self.log("scrcpy não encontrado no PATH.")
            return
        buffer_val = self.buffer_var.get().strip()
        if not buffer_val.isdigit():
            self.log("Buffer inválido.")
            return
        args = [
            exe,
            "--no-window",
            "--no-video",
            "--audio-source=playback",
            f"--audio-buffer={buffer_val}",
            f"--tcpip={ip}:{port}"
        ]
        try:
            creationflags = 0x08000000 if sys.platform.startswith("win") else 0
            proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
            self.scrcpy_proc = proc
            self.log(f"scrcpy iniciado (áudio) em {ip}:{port} (pid={proc.pid})")
        except Exception as e:
            self.log(f"Erro ao iniciar scrcpy: {e}")

    def disconnect(self):
        ip = self.ip_var.get().strip()
        port = self.port_var.get().strip()
        if ip and port:
            self.log(f"Desconectando {ip}:{port} ...")
            code, out = run_adb(["disconnect", f"{ip}:{port}"])
            self.log(f"[adb disconnect] retorno={code}. {out or ''}")
        else:
            self.log("IP/porta vazios — nada para desconectar.")
        if self.scrcpy_proc:
            try:
                pid = self.scrcpy_proc.pid
                self.scrcpy_proc.terminate()
                self.scrcpy_proc.wait(timeout=3)
                self.log(f"scrcpy (pid={pid}) terminado.")
            except Exception:
                try:
                    self.scrcpy_proc.kill()
                    self.log("scrcpy morto (kill).")
                except Exception as e:
                    self.log(f"Falha ao terminar scrcpy: {e}")
            finally:
                self.scrcpy_proc = None

    def on_close(self):
        self.log("Fechando — realizando desconexão...")
        try:
            self.disconnect()
        except Exception as e:
            self.log(f"Erro no disconnect: {e}")
        self.destroy()
        sys.exit(0)

    def _signal_handler(self, signum, frame):
        self.log("Sinal recebido (SIGINT). Executando desconexão...")
        try:
            self.disconnect()
        except Exception as e:
            self.log(f"Erro no disconnect: {e}")
        try:
            self.quit()
        except:
            pass
        sys.exit(0)

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()

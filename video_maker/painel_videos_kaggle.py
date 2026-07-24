import os
import sys
import re
import time
import requests
import threading
import subprocess
import customtkinter as ctk

# Configurações do CustomTkinter (Visual Premium)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VideoStudioKaggleApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("StatsFut - Fábrica de Vídeos (Kaggle Edition)")
        self.geometry("1100x750")
        self.resizable(False, False)
        
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Layout Principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        main_frame.grid_columnconfigure((0, 1), weight=1)
        main_frame.grid_rowconfigure(2, weight=1)

        # Título
        title_label = ctk.CTkLabel(main_frame, text="⚡ FÁBRICA DE VÍDEOS (KAGGLER V1)", font=ctk.CTkFont(family="Inter", size=32, weight="bold"), text_color="#8b5cf6")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 5))
        
        subtitle = ctk.CTkLabel(main_frame, text="Baixe áudios automáticos do site e gere vídeos sem copiar roteiros manuais.", text_color="#94a3b8")
        subtitle.grid(row=1, column=0, columnspan=2, pady=(0, 20))

        # --- PAINEL DE CONFIGURAÇÃO (Esquerda) ---
        config_frame = ctk.CTkFrame(main_frame, fg_color="#0f172a", border_width=1, border_color="#8b5cf6", corner_radius=12)
        config_frame.grid(row=2, column=0, padx=(0, 10), sticky="nsew")
        config_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(config_frame, text="⚙️ Integração Automática", font=ctk.CTkFont(size=18, weight="bold"), text_color="white").pack(anchor="w", padx=20, pady=(20, 15))

        # URL da partida
        ctk.CTkLabel(config_frame, text="URL da Partida no Statsfut", font=ctk.CTkFont(weight="bold"), text_color="#cbd5e1").pack(anchor="w", padx=20)
        self.entry_url = ctk.CTkEntry(config_frame, placeholder_text="https://statsfut.com/pt-br/match/123/...", height=38, fg_color="#1e293b", border_color="#475569")
        self.entry_url.pack(fill="x", padx=20, pady=(0, 20))

        # Seletor de Formato
        ctk.CTkLabel(config_frame, text="Formato do Vídeo a ser Gerado", font=ctk.CTkFont(weight="bold"), text_color="#cbd5e1").pack(anchor="w", padx=20)
        self.format_selector = ctk.CTkSegmentedButton(
            config_frame, 
            values=["🎬 YouTube (Longo)", "📱 TikTok (Curto)"], 
            font=ctk.CTkFont(size=13, weight="bold"),
            selected_color="#8b5cf6",
            selected_hover_color="#7c3aed",
            unselected_color="#1e293b",
            unselected_hover_color="#334155"
        )
        self.format_selector.set("🎬 YouTube (Longo)")
        self.format_selector.pack(fill="x", padx=20, pady=(0, 30))

        # Info Box
        info_frame = ctk.CTkFrame(config_frame, fg_color="#1e1b4b", border_width=1, border_color="#4338ca", corner_radius=8)
        info_frame.pack(fill="x", padx=20, pady=(0, 40))
        
        info_text = (
            "💡 Instruções de uso:\n"
            "1. Acesse o site de produção, abra o jogo e gere o roteiro.\n"
            "2. No modal do roteiro, clique em 'Gerar Áudio da Voz' via Kaggle.\n"
            "3. Quando o áudio estiver pronto no site, copie a URL do jogo,\n"
            "   cole aqui e clique no botão abaixo para fabricar o vídeo!"
        )
        ctk.CTkLabel(info_frame, text=info_text, font=ctk.CTkFont(size=12), text_color="#a5b4fc", justify="left", anchor="w").pack(padx=15, pady=15)

        # Botão Ação
        self.btn_fabricar = ctk.CTkButton(
            config_frame, 
            text="🚀 FABRICAR VÍDEO AUTOMÁTICO", 
            fg_color="#8b5cf6", 
            hover_color="#7c3aed", 
            font=ctk.CTkFont(size=16, weight="bold"), 
            height=50, 
            command=self.start_generation
        )
        self.btn_fabricar.pack(fill="x", padx=20, pady=(10, 20))

        # --- PAINEL DE TERMINAL (Direita) ---
        term_frame = ctk.CTkFrame(main_frame, fg_color="#0f172a", border_width=1, border_color="#8b5cf6", corner_radius=12)
        term_frame.grid(row=2, column=1, padx=(10, 0), sticky="nsew")
        term_frame.grid_rowconfigure(1, weight=1)
        term_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(term_frame, text="💻 Terminal de Produção", font=ctk.CTkFont(size=18, weight="bold"), text_color="white").grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        self.textbox_log = ctk.CTkTextbox(term_frame, fg_color="#000000", text_color="#4ade80", font=ctk.CTkFont(family="Courier", size=12))
        self.textbox_log.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.textbox_log.insert("0.0", "> Pronto para fabricação automática via Kaggle...\n")
        self.textbox_log.configure(state="disabled")
        
        self.process = None

    def log(self, message):
        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", message + "\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")

    def start_generation(self):
        if self.process and self.process.poll() is None:
            self.log("[ERRO] Uma renderização já está ativa! Aguarde.")
            return

        url = self.entry_url.get().strip()
        format_choice = self.format_selector.get()
        format_type = "short" if "TikTok" in format_choice else "long"

        if not url:
            self.log("[ERRO] Cole a URL da partida do Statsfut!")
            return

        # Extrair ID da partida da URL
        match_id_match = re.search(r'/match/(\d+)/', url)
        if not match_id_match:
            self.log("[ERRO] URL inválida! Certifique-se de que é a URL da partida contendo /match/ID/")
            return
            
        match_id = match_id_match.group(1)

        self.textbox_log.configure(state="normal")
        self.textbox_log.delete("0.0", "end")
        self.textbox_log.configure(state="disabled")
        self.log(f"> Buscando áudio e script da Partida ID: {match_id}...")

        # Roda em thread para não travar a interface
        thread = threading.Thread(target=self.download_and_run, args=(url, match_id, format_type))
        thread.start()

    def download_and_run(self, match_url, match_id, format_type):
        # 1. Definir caminhos de download
        temp_dir = os.path.join(self.base_dir, 'media', 'videos', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        audio_local_path = os.path.join(temp_dir, f'kaggle_audio_{match_id}.mp3')
        script_local_path = os.path.join(temp_dir, f'kaggle_script_{match_id}.txt')
        json_local_path = os.path.join(temp_dir, f'kaggle_timeline_{match_id}.json')
        
        # 2. Detectar Base URL Dinamicamente da URL da Partida
        # Ex: se colar http://127.0.0.1:8000/..., puxa local. Se colar https://statsfut.com/..., puxa do prod.
        parsed_url_match = re.match(r'(https?://[^/]+)', match_url)
        if parsed_url_match:
            prod_base_url = parsed_url_match.group(1)
        else:
            prod_base_url = "https://statsfut.com"
            
        
        self.log(f"> Conectando ao servidor ({prod_base_url}) para baixar recursos...")
        
        try:
            import time
            ts = int(time.time())
            
            # 1. Baixar o Áudio
            audio_remote_url = f"{prod_base_url}/api/dl-audio/match_{match_id}.mp3?t={ts}"
            self.log(f"> Baixando áudio principal: {audio_remote_url}")
            r_audio = requests.get(audio_remote_url, timeout=30)
            if r_audio.status_code != 200:
                self.log(f"[ERRO] O áudio do jogo ainda não foi gerado no site de produção!")
                self.log(f"Acesse o jogo no site, clique em 'Vídeo Express (Kaggle)' e gere o áudio antes.")
                return
                
            with open(audio_local_path, 'wb') as f:
                f.write(r_audio.content)
            self.log("✅ Áudio baixado com sucesso.")
            
            # 2. Baixar o Roteiro
            script_remote_url = f"{prod_base_url}/api/dl-audio/match_{match_id}.txt?t={ts}"
            self.log(f"> Baixando roteiro: {script_remote_url}")
            r_script = requests.get(script_remote_url, timeout=15)
            if r_script.status_code != 200:
                self.log(f"[ERRO] O arquivo de roteiro de máquina correspondente não foi achado no site.")
                return
                
            with open(script_local_path, 'w', encoding='utf-8') as f:
                f.write(r_script.text)
            self.log("✅ Roteiro de tags baixado com sucesso.")
            
            # 2.5 Baixar o JSON do Cronograma do Whisper
            json_remote_url = f"{prod_base_url}/api/dl-audio/match_{match_id}.json?t={ts}"
            self.log(f"> Baixando cronograma IA: {json_remote_url}")
            r_json = requests.get(json_remote_url, timeout=15)
            if r_json.status_code == 200:
                with open(json_local_path, 'wb') as f:
                    f.write(r_json.content)
                self.log("✅ Cronograma Whisper baixado com sucesso (Aceleração Híbrida!).")
            else:
                self.log("⚠️ Arquivo JSON não encontrado (Vídeo será gerado no modo lento via Whisper local).")
                json_local_path = "" # Se não existir, não passa pro script
                
            
        except Exception as e:
            self.log(f"[ERRO CONEXÃO] Falha ao baixar arquivos do servidor: {str(e)}")
            return
            
        # 3. Executar o script correspondente
        script_name = "gerar_video.py" if format_type == 'long' else "gerar_video_curto.py"
        script_path = os.path.join(self.base_dir, "video_maker", script_name)
        
        venv_python = os.path.join(self.base_dir, "venv", "Scripts", "python.exe")
        if not os.path.exists(venv_python):
            venv_python = "python"
            
        cmd = [
            venv_python, "-u", script_path,
            "--url", match_url,
            "--audio", audio_local_path,
            "--roteiro", script_local_path
        ]
        
        if json_local_path and os.path.exists(json_local_path):
            cmd.extend(["--json", json_local_path])

        self.log(f"\n> Iniciando motor local: {script_name}...")
        self.btn_fabricar.configure(state="disabled", text="⏳ Gravando Vídeo...")
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
            )
            
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.log(line.strip())
            
            self.process.stdout.close()
            self.process.wait()
            
            if self.process.returncode == 0:
                self.log("\n🎉 [CONCLUÍDO] Vídeo gravado e renderizado com sucesso!")
            else:
                self.log(f"\n❌ [ERRO] O motor retornou código de falha: {self.process.returncode}")
                
        except Exception as e:
            self.log(f"[ERRO LOCAL] {str(e)}")
        finally:
            self.btn_fabricar.configure(state="normal", text="🚀 FABRICAR VÍDEO AUTOMÁTICO")


if __name__ == "__main__":
    app = VideoStudioKaggleApp()
    app.mainloop()

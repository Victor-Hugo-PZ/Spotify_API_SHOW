import customtkinter as ctk
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image, ImageDraw
import requests
from io import BytesIO
import os  # Adicionado para podermos deletar o cache no Logout
from dotenv import load_dotenv
import threading
import google.generativeai as genai

# --- 1. CONFIGURAÇÕES VISUAIS ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

# --- 2. CARREGAR CREDENCIAIS DO .ENV ---
load_dotenv()
CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')


SCOPE = 'user-top-read user-read-recently-played'

class SpotifyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Spotify Alfredo")
        self.geometry("1050x700")
        
        self.bg_color = "#121212"
        self.sidebar_color = "#000000"
        self.card_color = "#181818"
        self.accent_color = "#1DB954"
        
        # --- CONFIGURAÇÃO GEMINI ---
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
        
        self.configure(fg_color=self.bg_color)
        
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE
        ))
        self.user_info = None
        self.deezer_cache = {} # Cache para evitar buscas repetidas no Deezer
        self.time_range = 'short_term' # Período padrão: 4 semanas
        self.aba_atual = "recentes" # Aba inicial padrão
        
        self.setup_layout()
        self.tentar_login_automatico()

    def setup_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # --- MENU LATERAL ---
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=self.sidebar_color)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        # Faz a linha 5 "empurrar" o botão de logout para o fundo
        self.sidebar_frame.grid_rowconfigure(5, weight=1) 
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Spotify Alfredo", font=ctk.CTkFont(size=26, weight="bold"), text_color=self.accent_color)
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))
        
        self.profile_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.profile_frame.grid(row=1, column=0, padx=20, pady=10)
        
        self.login_btn = ctk.CTkButton(self.profile_frame, text="Fazer Login", command=self.fazer_login, fg_color=self.accent_color, hover_color="#1ed760")
        self.login_btn.pack(pady=10)
        
        # Botões sem Emojis
        btn_font = ctk.CTkFont(size=15, weight="bold")
        
        self.btn_artistas = ctk.CTkButton(self.sidebar_frame, text="Top 10 Artistas", command=self.mostrar_artistas, state="disabled", fg_color="transparent", text_color="#FFFFFF", hover_color="#282828", font=btn_font, corner_radius=8, height=40)
        self.btn_artistas.grid(row=2, column=0, padx=20, pady=8, sticky="ew")
        
        self.btn_musicas = ctk.CTkButton(self.sidebar_frame, text="Top 10 Músicas", command=self.mostrar_musicas, state="disabled", fg_color="transparent", text_color="#FFFFFF", hover_color="#282828", font=btn_font, corner_radius=8, height=40)
        self.btn_musicas.grid(row=3, column=0, padx=20, pady=8, sticky="ew")
        
        self.btn_recentes = ctk.CTkButton(self.sidebar_frame, text="Últimas Ouvidas", command=self.mostrar_recentes, state="disabled", fg_color="transparent", text_color="#FFFFFF", hover_color="#282828", font=btn_font, corner_radius=8, height=40)
        self.btn_recentes.grid(row=4, column=0, padx=20, pady=8, sticky="ew")
        
        self.btn_alfredo = ctk.CTkButton(self.sidebar_frame, text="Alfredo (IA)", command=self.mostrar_alfredo, state="disabled", fg_color="transparent", text_color="#FFFFFF", hover_color="#282828", font=btn_font, corner_radius=8, height=40)
        self.btn_alfredo.grid(row=5, column=0, padx=20, pady=8, sticky="ew")
        
        # Botão de Logout (Fica escondido no começo)
        self.logout_btn = ctk.CTkButton(self.sidebar_frame, text="Sair da Conta", command=self.fazer_logout, fg_color="#2A1010", text_color="#FF4B4B", hover_color="#441010", font=ctk.CTkFont(size=13), corner_radius=8)
        self.logout_btn.grid(row=7, column=0, pady=20)
        self.logout_btn.grid_remove() # Esconde até estar logado
        
        # --- ÁREA PRINCIPAL ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=30, pady=30, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        # --- BOTÕES DE PERÍODO (Time Range) ---
        self.time_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.time_frame.pack(side="right", padx=(10, 0), pady=5)
        
        time_btn_font = ctk.CTkFont(size=12, weight="bold")
        
        # Dimensões fixas para evitar cortes e manter consistência
        btn_w = 110
        btn_h = 32
        btn_r = 16
        
        # Cores consistentes
        self.btn_4_semanas = ctk.CTkButton(self.time_frame, text="4 Semanas", width=btn_w, height=btn_h, font=time_btn_font, corner_radius=btn_r, command=lambda: self.mudar_periodo('short_term'), fg_color=self.accent_color, text_color="#000000", hover_color="#1DB954", border_width=0)
        self.btn_4_semanas.pack(side="left", padx=5)
        
        self.btn_6_meses = ctk.CTkButton(self.time_frame, text="6 Meses", width=btn_w, height=btn_h, font=time_btn_font, corner_radius=btn_r, command=lambda: self.mudar_periodo('medium_term'), fg_color="#282828", text_color="#FFFFFF", hover_color="#333333", border_width=0)
        self.btn_6_meses.pack(side="left", padx=5)
        
        self.btn_todo_tempo = ctk.CTkButton(self.time_frame, text="Todo Tempo", width=btn_w, height=btn_h, font=time_btn_font, corner_radius=btn_r, command=lambda: self.mudar_periodo('long_term'), fg_color="#282828", text_color="#FFFFFF", hover_color="#333333", border_width=0)
        self.btn_todo_tempo.pack(side="left", padx=5)
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Bem-vindo!", font=ctk.CTkFont(size=28, weight="bold"))
        self.title_label.pack(side="left")
        
        self.scroll_area = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent")
        self.scroll_area.grid(row=1, column=0, sticky="nsew")

    def tentar_login_automatico(self):
        try:
            self.user_info = self.sp.current_user()
            self.atualizar_ui_logado()
        except Exception:
            pass

    def fazer_login(self):
        try:
            self.user_info = self.sp.current_user()
            self.atualizar_ui_logado()
        except Exception:
            print("Erro no login. Verifique o terminal.")

    def fazer_logout(self):
        # 1. Deleta o cache do Spotify se ele existir
        if os.path.exists(".cache"):
            os.remove(".cache")
            
        # 2. Reseta a variável de usuário
        self.user_info = None
        
        # 3. Limpa o menu de perfil e recria o botão de login
        for widget in self.profile_frame.winfo_children():
            widget.destroy()
        self.login_btn = ctk.CTkButton(self.profile_frame, text="Fazer Login", command=self.fazer_login, fg_color=self.accent_color, hover_color="#1ed760")
        self.login_btn.pack(pady=10)
        
        # 4. Esconde logout, desativa botões e limpa tela principal
        self.logout_btn.grid_remove()
        self.btn_artistas.configure(state="disabled", fg_color="transparent", text_color="#FFFFFF")
        self.btn_musicas.configure(state="disabled", fg_color="transparent", text_color="#FFFFFF")
        self.btn_recentes.configure(state="disabled", fg_color="transparent", text_color="#FFFFFF")
        self.btn_alfredo.configure(state="disabled", fg_color="transparent", text_color="#FFFFFF")
        
        self.title_label.configure(text="Bem-vindo! Faça login para começar.")
        self.limpar_scroll_area()

    def atualizar_ui_logado(self):
        self.login_btn.pack_forget()
        
        nome = self.user_info['display_name']
        lbl_nome = ctk.CTkLabel(self.profile_frame, text=nome, font=ctk.CTkFont(weight="bold", size=16))
        
        if len(self.user_info['images']) > 0:
            url_foto = self.user_info['images'][0]['url']
            
            # Label para a foto (Sem borda acinzentada, a imagem será arredondada via PIL)
            self.lbl_foto_perfil = ctk.CTkLabel(self.profile_frame, text="", width=100, height=100, fg_color="transparent")
            self.lbl_foto_perfil.pack(pady=(0, 10))
            
            lbl_nome.pack() # Nome vem depois da foto
            
            def carregar_foto_perfil():
                try:
                    # 1. Baixa a imagem
                    resposta = requests.get(url_foto, timeout=5)
                    img_pillow = Image.open(BytesIO(resposta.content)).convert("RGBA")
                    
                    # 2. Prepara o corte quadrado (100x100)
                    largura, altura = img_pillow.size
                    tamanho = min(largura, altura)
                    img_cortada = img_pillow.crop(((largura - tamanho)/2, (altura - tamanho)/2, (largura + tamanho)/2, (altura + tamanho)/2)).resize((100, 100))
                    
                    # --- ARREDONDAR CANTOS DA IMAGEM E ADICIONAR BORDA VIA PIL ---
                    from PIL import ImageDraw
                    
                    # 3. Cria a máscara para o arredondamento (um pouco menor que a borda)
                    mask = Image.new('L', (100, 100), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    # Arredondamento da foto (radius 14 para ficar dentro da borda de radius 15)
                    draw_mask.rounded_rectangle((2, 2, 97, 97), radius=14, fill=255)
                    
                    # 4. Aplica o arredondamento na foto
                    img_arredondada = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
                    img_arredondada.paste(img_cortada, (0, 0), mask=mask)
                    
                    # 5. Adiciona a borda branca fina por cima de tudo
                    draw_border = ImageDraw.Draw(img_arredondada)
                    # outline=white, width=2 (borda fina)
                    # Usamos 1,1 a 98,98 para garantir que a borda não seja cortada
                    draw_border.rounded_rectangle((1, 1, 98, 98), radius=15, outline="#F2F0EF", width=2)
                    
                    # 6. Cria a imagem do CTK
                    self.img_perfil_ctk = ctk.CTkImage(light_image=img_arredondada, dark_image=img_arredondada, size=(100, 100))
                    
                    # 7. Atualiza a UI na thread principal
                    def atualizar_ui():
                        if hasattr(self, 'lbl_foto_perfil') and self.lbl_foto_perfil.winfo_exists():
                            self.lbl_foto_perfil.configure(image=self.img_perfil_ctk)
                    
                    self.after(0, atualizar_ui)
                except Exception as e:
                    print(f"Erro ao carregar foto: {e}")
            
            threading.Thread(target=carregar_foto_perfil, daemon=True).start()
        else:
            lbl_nome.pack(pady=20)
        
        self.btn_artistas.configure(state="normal")
        self.btn_musicas.configure(state="normal")
        self.btn_recentes.configure(state="normal")
        self.btn_alfredo.configure(state="normal")
        
        self.logout_btn.grid() # Mostra o botão de logout
        self.logout_btn.configure(fg_color="#2A1010", text_color="#FF4B4B", hover_color="#441010")
        self.mostrar_recentes()

    def destacar_botao_ativo(self, botao_ativo):
        # Cores para o menu lateral
        bg_active = self.accent_color
        bg_inactive = "transparent"
        text_active = "#000000"
        text_inactive = "#FFFFFF"
        
        # Resetar todos os botões do menu lateral para o estado inativo
        for btn in [self.btn_artistas, self.btn_musicas, self.btn_recentes, self.btn_alfredo]:
            btn.configure(fg_color=bg_inactive, text_color=text_inactive, hover_color="#282828", border_width=0)
            
        # Destacar apenas o botão ativo
        botao_ativo.configure(fg_color=bg_active, text_color=text_active, hover_color="#1DB954")

    def mudar_periodo(self, novo_range):
        self.time_range = novo_range
        
        # Estilos consistentes para o estado ativo e inativo (Sem bordas para evitar ghosting)
        bg_active = self.accent_color
        bg_inactive = "#282828"
        hover_active = "#1DB954" # Verde um pouco mais escuro para o hover do ativo
        hover_inactive = "#333333"
        
        # Atualiza visual dos botões de período
        self.btn_4_semanas.configure(fg_color=bg_active if novo_range == 'short_term' else bg_inactive, 
                                    text_color="#000000" if novo_range == 'short_term' else "#FFFFFF",
                                    hover_color=hover_active if novo_range == 'short_term' else hover_inactive)
        
        self.btn_6_meses.configure(fg_color=bg_active if novo_range == 'medium_term' else bg_inactive, 
                                  text_color="#000000" if novo_range == 'medium_term' else "#FFFFFF",
                                  hover_color=hover_active if novo_range == 'medium_term' else hover_inactive)
        
        self.btn_todo_tempo.configure(fg_color=bg_active if novo_range == 'long_term' else bg_inactive, 
                                     text_color="#000000" if novo_range == 'long_term' else "#FFFFFF",
                                     hover_color=hover_active if novo_range == 'long_term' else hover_inactive)
        
        # Recarrega a aba atual com o novo período
        if self.aba_atual == "artistas":
            self.mostrar_artistas()
        elif self.aba_atual == "musicas":
            self.mostrar_musicas()
        # 'recentes' não muda com time_range na API do Spotify, mas mantemos por consistência

    def mostrar_alfredo(self):
        self.aba_atual = "alfredo"
        self.time_frame.pack_forget() # Oculta os botões de tempo
        self.destacar_botao_ativo(self.btn_alfredo)
        self.title_label.configure(text="Conversar com Alfredo")
        self.limpar_scroll_area()
        
        # Container do Chat
        self.chat_container = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.chat_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Área de mensagens (Scrollable)
        self.chat_box = ctk.CTkTextbox(self.chat_container, fg_color="#121212", text_color="#FFFFFF", font=ctk.CTkFont(size=14), corner_radius=10, border_width=1, border_color="#333333")
        self.chat_box.pack(fill="both", expand=True, pady=(0, 15))
        self.chat_box.configure(state="disabled") # Somente leitura inicialmente
        
        # Input de texto
        self.input_frame = ctk.CTkFrame(self.chat_container, fg_color="transparent")
        self.input_frame.pack(fill="x")
        
        self.chat_input = ctk.CTkEntry(self.input_frame, placeholder_text="Pergunte ao Alfredo sobre seu gosto musical...", height=45, font=ctk.CTkFont(size=14), corner_radius=22, border_width=1, border_color="#404040", fg_color="#181818")
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.chat_input.bind("<Return>", lambda e: self.enviar_pergunta_alfredo())
        
        self.send_btn = ctk.CTkButton(self.input_frame, text="Enviar", width=80, height=45, corner_radius=22, fg_color=self.accent_color, text_color="#000000", font=ctk.CTkFont(size=14, weight="bold"), command=self.enviar_pergunta_alfredo)
        self.send_btn.pack(side="right")

        # Mensagem inicial de boas-vindas do Alfredo
        self.adicionar_mensagem_chat("Alfredo", "Olá! Sou o Alfredo, seu assistente musical. Estou analisando seu histórico para conversarmos. Como posso te ajudar hoje?")

    def adicionar_mensagem_chat(self, autor, mensagem):
        self.chat_box.configure(state="normal")
        tag = f"\n[{autor}]: "
        self.chat_box.insert("end", tag)
        self.chat_box.insert("end", f"{mensagem}\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def enviar_pergunta_alfredo(self):
        pergunta = self.chat_input.get().strip()
        if not pergunta:
            return
            
        self.chat_input.delete(0, "end")
        self.adicionar_mensagem_chat("Você", pergunta)
        
        if not self.model:
            self.adicionar_mensagem_chat("Alfredo", "Ops! Minha chave de API (Gemini) não foi configurada no arquivo .env. Peça para o mestre configurar GEMINI_API_KEY.")
            return

        # Rodar a análise em uma thread para não travar a UI
        threading.Thread(target=self.processar_resposta_alfredo, args=(pergunta,), daemon=True).start()

    def processar_resposta_alfredo(self, pergunta):
        try:
            # 1. Coletar dados do Spotify para o contexto (Top artistas e músicas de diferentes períodos)
            top_artistas_short = self.sp.current_user_top_artists(limit=10, time_range='short_term')['items']
            top_artistas_med = self.sp.current_user_top_artists(limit=10, time_range='medium_term')['items']
            top_artistas_long = self.sp.current_user_top_artists(limit=10, time_range='long_term')['items']
            
            top_tracks_short = self.sp.current_user_top_tracks(limit=10, time_range='short_term')['items']
            top_tracks_med = self.sp.current_user_top_tracks(limit=10, time_range='medium_term')['items']
            top_tracks_long = self.sp.current_user_top_tracks(limit=10, time_range='long_term')['items']

            # 2. Formatar o contexto para a IA
            contexto = f"""
            Você é o Alfredo, um assistente de música inteligente e amigável.
            Aqui está o histórico musical do usuário:
            
            ÚLTIMO MÊS (Short Term):
            - Artistas: {', '.join([a['name'] for a in top_artistas_short])}
            - Músicas: {', '.join([t['name'] for t in top_tracks_short])}
            
            ÚLTIMOS 6 MESES (Medium Term):
            - Artistas: {', '.join([a['name'] for a in top_artistas_med])}
            - Músicas: {', '.join([t['name'] for t in top_tracks_med])}
            
            TODO O TEMPO (Long Term):
            - Artistas: {', '.join([a['name'] for a in top_artistas_long])}
            - Músicas: {', '.join([t['name'] for t in top_tracks_long])}
            
            Tarefa: Analise a evolução musical do usuário, compare os períodos e responda à pergunta dele.
            Seja direto, divertido e dê sugestões baseadas nesse gosto. Use um tom de especialista em música.
            Pergunta do usuário: {pergunta}
            """
            
            # 3. Chamar o Gemini
            response = self.model.generate_content(contexto)
            resposta_texto = response.text
            
            # 4. Mostrar na UI
            self.after(0, lambda: self.adicionar_mensagem_chat("Alfredo", resposta_texto))
            
        except Exception as e:
            self.after(0, lambda: self.adicionar_mensagem_chat("Alfredo", f"Desculpe, tive um problema ao analisar seus dados: {str(e)}"))

    def limpar_scroll_area(self):
        for widget in self.scroll_area.winfo_children():
            widget.destroy()

    # --- CARD AGORA COM SUPORTE A IMAGEM E ESTATÍSTICAS (ASSÍNCRONO) ---
    def criar_card(self, numero, titulo, subtitulo, url_imagem=None, estatistica=None):
        card = ctk.CTkFrame(self.scroll_area, fg_color=self.card_color, corner_radius=8)
        card.pack(fill="x", pady=6, padx=5)
        
        # O número (#1, #2)
        num_label = ctk.CTkLabel(card, text=f"#{numero}", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.accent_color, width=40)
        num_label.pack(side="left", padx=15, pady=10)
        
        # Placeholder para a imagem (enquanto carrega em segundo plano)
        lbl_img = ctk.CTkLabel(card, text="", width=50, height=50)
        lbl_img.pack(side="left", padx=(0, 15))
        
        if url_imagem:
            def carregar_imagem():
                try:
                    resposta = requests.get(url_imagem, timeout=5)
                    img_pillow = Image.open(BytesIO(resposta.content))
                    
                    largura, altura = img_pillow.size
                    tamanho = min(largura, altura)
                    img_cortada = img_pillow.crop(((largura - tamanho)/2, (altura - tamanho)/2, (largura + tamanho)/2, (altura + tamanho)/2)).resize((50, 50))
                    
                    img_ctk = ctk.CTkImage(light_image=img_cortada, dark_image=img_cortada, size=(50, 50))
                    # Atualiza a imagem na UI de forma segura
                    self.after(0, lambda: lbl_img.configure(image=img_ctk))
                except:
                    pass
            
            threading.Thread(target=carregar_imagem, daemon=True).start()

        # Textos (Título e Subtítulo)
        text_frame = ctk.CTkFrame(card, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Título com efeito Marquee (Rolar ao passar o mouse)
        limit_chars = 50
        titulo_curto = titulo[:limit_chars] + "..." if len(titulo) > limit_chars else titulo
        lbl_titulo = ctk.CTkLabel(text_frame, text=titulo_curto, font=ctk.CTkFont(size=15, weight="bold"), anchor="w")
        lbl_titulo.pack(fill="x")
        
        if len(titulo) > limit_chars:
            lbl_titulo.marquee_running = False
            lbl_titulo.original_text = titulo + "   |   "
            
            def iniciar_marquee(event, label=lbl_titulo):
                if not label.marquee_running:
                    label.marquee_running = True
                    rolar_texto(label, label.original_text)

            def parar_marquee(event, label=lbl_titulo):
                label.marquee_running = False
                label.configure(text=titulo_curto)

            def rolar_texto(label, texto_full):
                if label.marquee_running:
                    novo_texto = texto_full[1:] + texto_full[0]
                    label.configure(text=novo_texto[:limit_chars])
                    self.after(150, lambda: rolar_texto(label, novo_texto))

            lbl_titulo.bind("<Enter>", iniciar_marquee)
            lbl_titulo.bind("<Leave>", parar_marquee)
        
        lbl_sub = ctk.CTkLabel(text_frame, text=subtitulo, font=ctk.CTkFont(size=12), text_color="#A0A0A0", anchor="w")
        lbl_sub.pack(fill="x")

        # Estatísticas (Streams/Popularidade) - Lado Direito
        stats_label = ctk.CTkLabel(card, text=estatistica if estatistica else "", font=ctk.CTkFont(size=13, weight="bold"), text_color=self.accent_color)
        stats_label.pack(side="right", padx=20)
        
        return stats_label, lbl_sub # Retorna também o label do subtítulo para o Top Artistas

    # --- FUNÇÕES DE BUSCA ---
    def buscar_rank_no_deezer(self, nome_musica, nome_artista):
        # Chave do cache para evitar buscas repetidas
        cache_key = f"{nome_musica} - {nome_artista}"
        if cache_key in self.deezer_cache:
            return self.deezer_cache[cache_key]

        try:
            # Busca a música específica no Deezer para pegar o Rank (Proxy de streams)
            query = f"track:\"{nome_musica}\" artist:\"{nome_artista}\""
            url = f"https://api.deezer.com/search?q={query}&limit=1"
            resposta = requests.get(url, timeout=3).json()
            if 'data' in resposta and len(resposta['data']) > 0:
                rank = resposta['data'][0]['rank']
                # Formata o rank de forma legível
                if rank >= 1000000:
                    resultado = f"{rank/1000000:.1f}M"
                elif rank >= 1000:
                    resultado = f"{rank/1000:.0f}k"
                else:
                    resultado = str(rank)
                
                # Salva no cache
                self.deezer_cache[cache_key] = resultado
                return resultado
            return None
        except:
            return None

    def carregar_streams_async(self, label, nome_musica, nome_artista):
        def tarefa():
            try:
                rank = self.buscar_rank_no_deezer(nome_musica, nome_artista)
                if rank:
                    # Usa after para atualizar a UI de forma segura (thread-safe)
                    self.after(0, lambda: label.configure(text=f"Streams: {rank}"))
            except Exception as e:
                print(f"Erro na thread de streams: {e}")
        
        t = threading.Thread(target=tarefa, daemon=True)
        t.start()

    def carregar_detalhes_artista_async(self, label_stats, label_sub, artista_resumido, generos):
        def tarefa():
            try:
                nome_artista = artista_resumido.get('name', 'Artista')
                
                # 1. Busca o artista no Deezer para pegar o número de fãs (Proxy de Ouvintes Mensais)
                # O Spotify não fornece ouvintes mensais via API pública por questões de contrato.
                url_busca_artista = f"https://api.deezer.com/search/artist?q={nome_artista}&limit=1"
                res_artista = requests.get(url_busca_artista, timeout=5).json()
                
                ouvintes_formatado = "---"
                if 'data' in res_artista and len(res_artista['data']) > 0:
                    artista_id_deezer = res_artista['data'][0]['id']
                    # Busca detalhes do artista para pegar o campo 'nb_fan'
                    res_detalhes = requests.get(f"https://api.deezer.com/artist/{artista_id_deezer}", timeout=5).json()
                    fas = res_detalhes.get('nb_fan', 0)
                    
                    if fas >= 1000000:
                        ouvintes_formatado = f"{fas/1000000:.1f}M"
                    elif fas >= 1000:
                        ouvintes_formatado = f"{fas/1000:.0f}k"
                    else:
                        ouvintes_formatado = str(fas)

                # 2. Busca o Top Hit no Deezer
                url_deezer = f"https://api.deezer.com/search?q=artist:\"{nome_artista}\"&limit=1"
                resposta_deezer = requests.get(url_deezer, timeout=5).json()
                hit = resposta_deezer['data'][0]['title'] if 'data' in resposta_deezer and len(resposta_deezer['data']) > 0 else "Hit indisponível"
                
                # Atualiza a UI de forma segura
                novo_sub = f"{generos}  •  Top Hit: {hit}"
                estatistica_nova = f"Ouvintes: {ouvintes_formatado}"
                
                self.after(0, lambda: (
                    label_stats.configure(text=estatistica_nova),
                    label_sub.configure(text=novo_sub)
                ))
            except Exception as e:
                print(f"Erro ao carregar detalhes do artista: {e}")
                self.after(0, lambda: label_sub.configure(text=f"{generos}  •  Hit indisponível"))
        
        threading.Thread(target=tarefa, daemon=True).start()

    def mostrar_artistas(self):
        self.aba_atual = "artistas"
        self.time_frame.pack(side="right") # Garante que os botões de tempo apareçam
        self.destacar_botao_ativo(self.btn_artistas)
        self.title_label.configure(text="Seus Artistas Favoritos")
        self.limpar_scroll_area()
        
        try:
            top_artists = self.sp.current_user_top_artists(limit=10, time_range=self.time_range)
            
            for i, artista in enumerate(top_artists.get('items', [])):
                nome_artista = artista.get('name', 'Desconhecido')
                
                # Gêneros
                lista_generos = artista.get('genres', [])
                generos = " • ".join(lista_generos[:2]).title() if lista_generos else "Independente / Alternativo"
                
                # Estados iniciais (Placeholder)
                estatistica_inicial = "Ouvintes: ---"
                sub_inicial = f"{generos}  •  Carregando hit..."
                
                # Foto
                images = artista.get('images', [])
                url_foto = images[0]['url'] if images else None
                
                # Cria o card
                lbl_stats, lbl_sub = self.criar_card(i + 1, nome_artista, sub_inicial, url_foto, estatistica_inicial)
                
                # Dispara busca completa (Ouvintes + Hit) em background
                self.carregar_detalhes_artista_async(lbl_stats, lbl_sub, artista, generos)
                
        except Exception as e:
            print(f"Erro em mostrar_artistas: {e}")
            self.criar_card("!", "Erro", str(e))

    def mostrar_musicas(self):
        self.aba_atual = "musicas"
        self.time_frame.pack(side="right") # Garante que os botões de tempo apareçam
        self.destacar_botao_ativo(self.btn_musicas)
        self.title_label.configure(text="Suas Músicas Favoritas")
        self.limpar_scroll_area()
        
        try:
            top_tracks = self.sp.current_user_top_tracks(limit=10, time_range=self.time_range)
            if not top_tracks['items']:
                self.criar_card("?", "Sem dados", "Você ainda não ouviu músicas suficientes.")
                return

            for i, track in enumerate(top_tracks['items']):
                # Tenta pegar a capa de forma segura
                album = track.get('album', {})
                images = album.get('images', [])
                url_capa = images[0]['url'] if images else None
                
                # Popularidade pode não vir em todos os tipos de objetos da API
                pop = track.get('popularity', 0)
                estatistica_inicial = f"Streams: {pop}"
                
                # Cria o card e pega a referência do label de stats
                lbl_stats, _ = self.criar_card(i + 1, track.get('name', 'Música'), track['artists'][0]['name'] if track.get('artists') else 'Artista', url_capa, estatistica_inicial)
                
                # Dispara a busca do Deezer em segundo plano
                self.carregar_streams_async(lbl_stats, track['name'], track['artists'][0]['name'])
        except Exception as e:
            print(f"Erro em mostrar_musicas: {e}")
            self.criar_card("!", "Erro ao carregar", str(e))
        
    def mostrar_recentes(self):
        self.aba_atual = "recentes"
        self.time_frame.pack_forget() # Oculta os botões de tempo nesta aba
        self.destacar_botao_ativo(self.btn_recentes)
        self.title_label.configure(text="Tocadas Recentemente")
        self.limpar_scroll_area()
        
        try:
            recentes = self.sp.current_user_recently_played(limit=10)
            if not recentes['items']:
                self.criar_card("?", "Vazio", "Nenhuma música tocada recentemente.")
                return

            for i, item in enumerate(recentes['items']):
                track = item.get('track', {})
                # Tenta pegar a capa de forma segura
                album = track.get('album', {})
                images = album.get('images', [])
                url_capa = images[0]['url'] if images else None
                
                # 'popularity' raramente vem no objeto 'recently played' do Spotify
                pop = track.get('popularity', 0)
                estatistica_inicial = f"Streams: {pop}"
                
                lbl_stats, _ = self.criar_card(i + 1, track.get('name', 'Música'), track['artists'][0]['name'] if track.get('artists') else 'Artista', url_capa, estatistica_inicial)
                
                # Dispara a busca do Deezer em segundo plano
                self.carregar_streams_async(lbl_stats, track['name'], track['artists'][0]['name'])
        except Exception as e:
            print(f"Erro em mostrar_recentes: {e}")
            self.criar_card("!", "Erro ao carregar", str(e))

if __name__ == "__main__":
    app = SpotifyApp()
    app.mainloop()
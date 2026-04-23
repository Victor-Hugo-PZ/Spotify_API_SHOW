import os
import threading
import requests
import spotipy
import re
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image, ImageDraw
from io import BytesIO
import customtkinter as ctk
from dotenv import load_dotenv
from google import genai

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
        
        self.title("Spotify Al.fredo")
        self.geometry("1050x700")
        
        self.bg_color = "#121212"
        self.sidebar_color = "#000000"
        self.card_color = "#181818"
        self.accent_color = "#1DB954"
        
        # --- CONFIGURAÇÃO GEMINI ---
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        if self.gemini_key:
            # Usando o novo SDK google-genai
            self.gemini_client = genai.Client(api_key=self.gemini_key)
        else:
            self.gemini_client = None
        
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
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Spotify Al.fredo", font=ctk.CTkFont(size=26, weight="bold"), text_color=self.accent_color)
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
        
        self.btn_alfredo = ctk.CTkButton(self.sidebar_frame, text="Al.fredo", command=self.mostrar_alfredo, state="disabled", fg_color="transparent", text_color="#FFFFFF", hover_color="#282828", font=btn_font, corner_radius=8, height=40)
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
        self.btn_4_semanas = ctk.CTkButton(self.time_frame, text="1 Mês", width=btn_w, height=btn_h, font=time_btn_font, corner_radius=btn_r, command=lambda: self.mudar_periodo('short_term'), fg_color=self.accent_color, text_color="#000000", hover_color="#1DB954", border_width=0)
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
        # Limpa o frame de perfil para garantir que não haja duplicatas
        for widget in self.profile_frame.winfo_children():
            widget.destroy()
            
        if not self.user_info:
            return
            
        nome = self.user_info.get('display_name', 'Usuário')
        lbl_nome = ctk.CTkLabel(self.profile_frame, text=nome, font=ctk.CTkFont(weight="bold", size=16))
        
        if self.user_info.get('images') and len(self.user_info['images']) > 0:
            url_foto = self.user_info['images'][0]['url']
            
            # Label para a foto
            self.lbl_foto_perfil = ctk.CTkLabel(self.profile_frame, text="", width=100, height=100, fg_color="transparent")
            self.lbl_foto_perfil.pack(pady=(0, 10))
            
            lbl_nome.pack() # Nome vem depois da foto
            
            def carregar_foto_perfil():
                try:
                    resposta = requests.get(url_foto, timeout=5)
                    img_pillow = Image.open(BytesIO(resposta.content)).convert("RGBA")
                    
                    largura, altura = img_pillow.size
                    tamanho = min(largura, altura)
                    img_cortada = img_pillow.crop(((largura - tamanho)/2, (altura - tamanho)/2, (largura + tamanho)/2, (altura + tamanho)/2)).resize((100, 100))
                    
                    # Arredondar via PIL
                    mask = Image.new('L', (100, 100), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.rounded_rectangle((2, 2, 97, 97), radius=14, fill=255)
                    
                    img_arredondada = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
                    img_arredondada.paste(img_cortada, (0, 0), mask=mask)
                    
                    draw_border = ImageDraw.Draw(img_arredondada)
                    draw_border.rounded_rectangle((1, 1, 98, 98), radius=15, outline="#F2F0EF", width=2)
                    
                    self.img_perfil_ctk = ctk.CTkImage(light_image=img_arredondada, dark_image=img_arredondada, size=(100, 100))
                    
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
        
        self.logout_btn.grid() 
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
        self.aba_atual = "Al.fredo"
        self.time_frame.pack_forget() # Oculta os botões de tempo
        self.destacar_botao_ativo(self.btn_alfredo)
        self.title_label.configure(text="Al.fredo - Seu Assistente Musical")
        self.limpar_scroll_area()
        
        # Container Principal do Alfredo
        self.alfredo_container = ctk.CTkFrame(self.scroll_area, fg_color="transparent")
        self.alfredo_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame de Botões de Ação no topo
        self.acoes_frame = ctk.CTkFrame(self.alfredo_container, fg_color="transparent")
        self.acoes_frame.pack(fill="x", pady=(0, 20))
        
        btn_font = ctk.CTkFont(size=13, weight="bold")
        
        self.btn_evolucao = ctk.CTkButton(
            self.acoes_frame, 
            text="Analisar Minha Evolução Musical", 
            height=45, 
            font=btn_font, 
            corner_radius=22, 
            fg_color="#282828", 
            hover_color="#333333",
            command=lambda: self.solicitar_analise_alfredo("evolucao")
        )
        self.btn_evolucao.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_recomendacao = ctk.CTkButton(
            self.acoes_frame, 
            text="Recomendações Personalizadas", 
            height=45, 
            font=btn_font, 
            corner_radius=22, 
            fg_color=self.accent_color, 
            text_color="#000000",
            hover_color="#1DB954",
            command=lambda: self.solicitar_analise_alfredo("recomendacao")
        )
        self.btn_recomendacao.pack(side="left", fill="x", expand=True)

        # Área de Conteúdo (Onde aparecerá o texto e os cards)
        self.conteudo_alfredo = ctk.CTkFrame(self.alfredo_container, fg_color="transparent")
        self.conteudo_alfredo.pack(fill="both", expand=True)

        # Mensagem inicial amigável
        self.msg_inicial = ctk.CTkLabel(
            self.conteudo_alfredo, 
            text="Olá! Sou o Al.fredo.\nEscolha uma das opções acima para eu analisar seu perfil musical!",
            font=ctk.CTkFont(size=16),
            text_color="#B3B3B3",
            pady=40
        )
        self.msg_inicial.pack()

    def solicitar_analise_alfredo(self, tipo):
        if not self.gemini_client:
            self.limpar_conteudo_alfredo()
            lbl = ctk.CTkLabel(self.conteudo_alfredo, text="Ops! Chave Gemini não configurada no .env.", text_color="#FF4444")
            lbl.pack(pady=20)
            return

        # Limpa e mostra que está carregando
        self.limpar_conteudo_alfredo()
        self.loading_label = ctk.CTkLabel(self.conteudo_alfredo, text="Al.fredo está analisando seus dados...", font=ctk.CTkFont(size=16, weight="bold"))
        self.loading_label.pack(pady=40)
        
        threading.Thread(target=self.processar_resposta_alfredo, args=(tipo,), daemon=True).start()

    def limpar_conteudo_alfredo(self):
        for widget in self.conteudo_alfredo.winfo_children():
            widget.destroy()

    def processar_resposta_alfredo(self, tipo):
        try:
            # 1. Coletar dados do Spotify
            top_artistas_short = self.sp.current_user_top_artists(limit=15, time_range='short_term')['items']
            top_artistas_med = self.sp.current_user_top_artists(limit=15, time_range='medium_term')['items']
            top_artistas_long = self.sp.current_user_top_artists(limit=15, time_range='long_term')['items']
            
            top_tracks_short = self.sp.current_user_top_tracks(limit=15, time_range='short_term')['items']
            top_tracks_med = self.sp.current_user_top_tracks(limit=15, time_range='medium_term')['items']
            top_tracks_long = self.sp.current_user_top_tracks(limit=15, time_range='long_term')['items']

            # 2. Prompt focado em extrair texto, músicas e artistas separadamente
            if tipo == "evolucao":
                instrucao = f"""
                Analise a evolução musical do usuário de forma detalhada e iconica (entre 2-10 frases).
                Comente as músicas e artistas que você considera a virada de chave do usuário.
                Use este formato EXATO:
                TEXTO: [Sua análise iconica e detalhada]
                MUSICAS: [Musica 1], [Musica 2], [Musica 3]
                ARTISTAS: [Artista 1], [Artista 2], [Artista 3]

                DADOS : {', '.join([a['name'] for a in top_artistas_long])}
                DADOS : {', '.join([a['name'] for a in top_tracks_long])}

                """
            else:
                instrucao = f"""
                Recomende 3 bandas e 3 músicas baseadas no gosto atual. Seja iconico (máximo 3 frases).
                Use este formato EXATO:
                TEXTO: [Sua explicação iconica]
                MUSICAS: [Nome da Música 1], [Nome da Música 2], [Nome da Música 3]
                ARTISTAS: [Nome da Banda ou Artista 1], [Nome da Banda ou Artista 2], [Nome da Banda ou Artista 3]

                DADOS RECENTES: {', '.join([a['name'] for a in top_artistas_short])}
                DADOS RECENTES: {', '.join([a['name'] for a in top_tracks_short])}
                """

            contexto = f"""
            Você é o Al.fredo, assistente musical de elite. 
            Sinta-se livre para falar, os usuários amam ler suas frases iconicas.
            Use palavras estilizadas que combinem com o histórico musical do usuário (que esta no DADOS abaixo).
            Lembre de usar a quebra de linha após cada ponto final.
            {instrucao}
            """


            modelos_tentar = ['gemini-flash-latest', 'gemini-flash-lite-latest']
            resposta_bruta = None
            ultimo_erro = "Nenhum modelo respondeu"
            
            for modelo in modelos_tentar:
                try:
                    print(f"Tentando Al.fredo com modelo: {modelo}...")
                    response = self.gemini_client.models.generate_content(model=modelo, contents=contexto)
                    if response and response.text:
                        resposta_bruta = response.text
                        print(f"Sucesso com o modelo {modelo}!")
                        break
                except Exception as e_modelo:
                    ultimo_erro = str(e_modelo)
                    print(f"Erro no modelo {modelo}: {ultimo_erro}")
                    continue

            if not resposta_bruta:
                raise Exception(f"IA Indisponível: {ultimo_erro}")

            # 3. Parsear a resposta de forma mais flexível
            texto_analise = ""
            musicas_sugeridas = []
            artistas_sugeridos = []
            
            # Tenta encontrar as seções independentemente da ordem ou de labels "TEXT" vs "TEXTO"
            m_texto = re.search(r"TEXT(?:O)?:?\s*(.*?)(?=MUSICAS:|ARTISTAS:|$)", resposta_bruta, re.S | re.I)
            m_musicas = re.search(r"MUSICAS:?\s*(.*?)(?=TEXTO:|TEXT:|ARTISTAS:|$)", resposta_bruta, re.S | re.I)
            m_artistas = re.search(r"ARTISTAS:?\s*(.*?)(?=TEXTO:|TEXT:|MUSICAS:|$)", resposta_bruta, re.S | re.I)

            if m_texto: texto_analise = m_texto.group(1).strip()
            if m_musicas: musicas_sugeridas = [m.strip() for m in m_musicas.group(1).split(",") if m.strip()]
            if m_artistas: artistas_sugeridos = [a.strip() for a in m_artistas.group(1).split(",") if a.strip()]

            # Fallback se falhar o regex
            if not texto_analise and not musicas_sugeridas:
                texto_analise = resposta_bruta

            # 4. Atualizar UI de forma segura
            self.after(0, lambda: self.renderizar_resultado_alfredo(texto_analise, musicas_sugeridas, artistas_sugeridos))
            
        except Exception as e:
            msg_erro = str(e)
            self.after(0, lambda: self.renderizar_erro_alfredo(msg_erro))

    def renderizar_resultado_alfredo(self, texto, musicas, artistas):
        self.limpar_conteudo_alfredo()
        
        # Frame de Texto - Com bordas mais arredondadas para um ar mais tranquilo
        texto_frame = ctk.CTkFrame(
            self.conteudo_alfredo, 
            fg_color="#181818", 
            corner_radius=25, 
            border_width=1, 
            border_color="#333333"
        )
        texto_frame.pack(fill="x", pady=(0, 25), padx=10) # Reduzido padx de 20 para 10 para o card ocupar mais espaço

        # Usando CTKTextbox para permitir formatação de negrito
        self.txt_alfredo = ctk.CTkTextbox(
            texto_frame,
            fg_color="transparent",
            text_color="#EBEBEB",
            font=ctk.CTkFont(size=15),
            wrap="word",
            border_width=0,
            padx=15, 
            pady=15, 
            activate_scrollbars=False,
            height=100
        )
        self.txt_alfredo.pack(fill="x")
        
        # Configura a tag de negrito no widget interno do tkinter
        self.txt_alfredo._textbox.tag_configure("bold", font=ctk.CTkFont(size=15, weight="bold"))
        
        def inserir_texto_estilizado(widget, raw_text):
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            
            # Divide o texto pelos asteriscos
            partes = raw_text.split('*')
            for i, parte in enumerate(partes):
                if i % 2 == 1: # Texto que estava entre asteriscos
                    widget.insert("end", parte, "bold")
                else:
                    widget.insert("end", parte)
            
            widget.configure(state="disabled")
            
            # Ajuste dinâmico de altura baseado no texto inserido (contando linhas quebradas)
            def ajustar_altura():
                widget.update_idletasks()
                # Conta o número real de linhas exibidas (incluindo as quebradas automaticamente)
                res = widget._textbox.count("1.0", "end", "displaylines")
                num_linhas = res[0] if res else 1
                
                # Estimativa precisa: 22 pixels por linha + 30 de padding total
                nova_altura = (num_linhas * 22) + 30
                widget.configure(height=max(80, nova_altura))
            
            self.after(50, ajustar_altura)
            # Recalcula a altura se o card mudar de largura (redimensionamento da janela)
            widget.bind("<Configure>", lambda e: ajustar_altura())

        inserir_texto_estilizado(self.txt_alfredo, texto)
        
        # Container de Duas Colunas
        colunas_container = ctk.CTkFrame(self.conteudo_alfredo, fg_color="transparent")
        colunas_container.pack(fill="both", expand=True, padx=15)
        
        # Coluna de Músicas
        col_musicas = ctk.CTkFrame(colunas_container, fg_color="transparent")
        col_musicas.pack(side="left", fill="both", expand=True, padx=10)
        ctk.CTkLabel(col_musicas, text="🎵 MÚSICAS", font=ctk.CTkFont(size=14, weight="bold"), text_color=self.accent_color).pack(pady=(0, 10))
        
        for m in musicas[:3]:
            self.criar_card_alfredo(col_musicas, m, "track")
            
        # Coluna de Artistas
        col_artistas = ctk.CTkFrame(colunas_container, fg_color="transparent")
        col_artistas.pack(side="left", fill="both", expand=True, padx=10)
        ctk.CTkLabel(col_artistas, text="🎵 ARTISTAS", font=ctk.CTkFont(size=14, weight="bold"), text_color=self.accent_color).pack(pady=(0, 10))
        
        for a in artistas[:3]:
            self.criar_card_alfredo(col_artistas, a, "artist")

    def criar_card_alfredo(self, parent, nome, tipo):
        # Card com o mesmo estilo do resto do app
        card = ctk.CTkFrame(parent, fg_color=self.card_color, corner_radius=8, height=80)
        card.pack(fill="x", pady=5)
        card.pack_propagate(False)
        
        # Imagem ocupando toda a altura do card (80px), com margem à esquerda para um visual limpo
        lbl_img = ctk.CTkLabel(card, text="", width=80, height=80)
        lbl_img.pack(side="left", padx=(12, 0)) 
        
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        
        lbl_titulo = ctk.CTkLabel(info_frame, text=nome[:30], font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        lbl_titulo.pack(fill="x")
        
        lbl_sub = ctk.CTkLabel(info_frame, text="Carregando...", font=ctk.CTkFont(size=11), text_color="#A0A0A0", anchor="w")
        lbl_sub.pack(fill="x")
        
        def carregar_dados_card():
            try:
                # Busca no Spotify
                q = f"artist:\"{nome}\"" if tipo == "artist" else nome
                res = self.sp.search(q=q, limit=1, type=tipo)
                
                items = res['tracks']['items'] if tipo == "track" else res['artists']['items']
                if items:
                    item = items[0]
                    titulo = item['name']
                    
                    if tipo == "track":
                        sub = item['artists'][0]['name']
                        url_img = item['album']['images'][0]['url'] if item['album']['images'] else None
                    else:
                        sub = item['genres'][0].title() if item.get('genres') else "Artista"
                        url_img = item['images'][0]['url'] if item.get('images') else None
                    
                    # Atualiza textos
                    self.after(0, lambda: lbl_titulo.configure(text=titulo[:30]))
                    self.after(0, lambda: lbl_sub.configure(text=sub[:35]))
                    
                    # Carrega imagem
                    if url_img:
                        r = requests.get(url_img, timeout=5)
                        img_raw = Image.open(BytesIO(r.content)).convert("RGBA")
                        
                        # Corte quadrado (PIL) para 80x80
                        w, h = img_raw.size
                        size = min(w, h)
                        img_crop = img_raw.crop(((w-size)/2, (h-size)/2, (w+size)/2, (h+size)/2)).resize((80, 80))
                        
                        ctk_img = ctk.CTkImage(img_crop, size=(80, 80))
                        self.after(0, lambda: lbl_img.configure(image=ctk_img))
                else:
                    self.after(0, lambda: lbl_sub.configure(text="Não encontrado"))
            except:
                self.after(0, lambda: lbl_sub.configure(text="Erro ao carregar"))
                
        threading.Thread(target=carregar_dados_card, daemon=True).start()

    def renderizar_erro_alfredo(self, erro):
        self.limpar_conteudo_alfredo()
        msg = "O sistema está sobrecarregado. Tente novamente!" if "503" in erro else f"Erro: {erro}"
        ctk.CTkLabel(self.conteudo_alfredo, text=msg, text_color="#FF4444", font=ctk.CTkFont(size=14)).pack(pady=20)

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
# Spotify Alfredo - Dashboard Musical 🚀

Um dashboard elegante, moderno e inteligente construído com Python para transformar seus dados do Spotify em uma experiência visual premium.

## 🌟 Funcionalidades Principais

- **Alfredo (IA)**: Seu assistente musical pessoal. 
  - **Análise de Evolução**: Uma análise curta e inteligente do seu gosto musical ao longo do tempo.
  - **Recomendações de Elite**: Sugestões personalizadas de músicas e artistas baseadas no que você ouve.
  - **Interface Inteligente**: Cards dinâmicos com capas de álbuns, nomes de artistas e gêneros.
- **Top 10 Artistas**: Visualize seus artistas favoritos com dados de ouvintes mensais e seus maiores sucessos.
- **Top 10 Músicas**: Ranking das suas faixas mais ouvidas com capas em alta definição.
- **Últimas Ouvidas**: Histórico recente para você nunca perder aquela música que acabou de tocar.
- **Interface Premium**: Desenvolvido com `customtkinter` seguindo a identidade visual Dark Mode do Spotify.

## 🎨 Destaques de Design e UX

- **Cards de Alta Fidelidade**: Imagens com corte quadrado perfeito (1:1) e preenchimento total, seguindo o padrão das melhores interfaces de streaming.
- **Texto Dinâmico**: Sistema de `wraplength` automático que ajusta as análises da IA ao tamanho da janela, evitando cortes indesejados.
- **Visual Limpo**: Margens e espaçamentos (paddings) calculados para uma leitura confortável e moderna.
- **Perfil Estilizado**: Foto de perfil arredondada com borda fina e elegante no menu lateral.
- **Performance**: Carregamento assíncrono (threading) para garantir que a interface permaneça fluida enquanto busca dados.

## 🛠️ Tecnologias Utilizadas

- **Python 3.x**
- **Spotipy**: Integração completa com a API Web do Spotify.
- **Google Gemini AI**: Inteligência artificial de ponta para análise e recomendações.
- **CustomTkinter**: UI moderna com widgets customizados.
- **Pillow (PIL)**: Processamento avançado de imagens.
- **Requests**: Comunicação com APIs externas.
- **Python-dotenv**: Gestão segura de chaves de API.

## 📋 Configuração e Instalação

### 1. Requisitos de API
Você precisará de:
- Credenciais no [Spotify for Developers](https://developer.spotify.com/).
- Uma chave de API do [Google AI Studio (Gemini)](https://aistudio.google.com/).

### 2. Instalação
```bash
pip install customtkinter spotipy pillow python-dotenv requests google-genai
```

### 3. Variáveis de Ambiente (.env)
Crie um arquivo `.env` na raiz:
```env
SPOTIPY_CLIENT_ID='seu_id_aqui'
SPOTIPY_CLIENT_SECRET='seu_secret_aqui'
SPOTIPY_REDIRECT_URI='http://localhost:8888/callback'
GEMINI_API_KEY='sua_chave_gemini_aqui'
```

## 🏃 Como Iniciar
```bash
python app.py
```

---
**Spotify Alfredo** - Levando sua análise musical para o próximo nível com Inteligência Artificial. 🎵✨

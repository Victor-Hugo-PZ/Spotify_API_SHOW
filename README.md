# Spotify Alfredo - Dashboard Musical

Um dashboard elegante e moderno construído com Python para visualizar suas estatísticas do Spotify em tempo real.

## 🚀 Funcionalidades

- **Top 10 Artistas**: Veja seus artistas mais ouvidos recentemente, incluindo o número de ouvintes mensais (via Deezer) e o seu principal hit.
- **Top 10 Músicas**: Lista das suas faixas favoritas com contagem de streams estimada.
- **Últimas Ouvidas**: Histórico recente do que você andou escutando.
- **Interface Moderna**: Desenvolvido com `customtkinter` para um visual Dark Mode premium.
- **Carregamento Assíncrono**: Sistema de threads para garantir que a interface nunca trave enquanto busca dados das APIs.
- **Segurança**: Gerenciamento de credenciais via variáveis de ambiente (`.env`).

## 🛠️ Tecnologias Utilizadas

- **Python 3.x**
- **Spotipy**: Biblioteca para integração com a API do Spotify.
- **CustomTkinter**: Interface gráfica moderna e customizável.
- **Pillow (PIL)**: Processamento de imagens para fotos de perfil e capas.
- **Deezer API**: Utilizada como proxy para estatísticas de ouvintes e hits.
- **Python-dotenv**: Gerenciamento de configurações.

## 📋 Pré-requisitos

Antes de começar, você precisará:
1. Uma conta no [Spotify for Developers](https://developer.spotify.com/).
2. Criar um App no dashboard do Spotify para obter seu `Client ID` e `Client Secret`.
3. Configurar a `Redirect URI` como `http://localhost:8888/callback` (ou a de sua preferência).

## 🔧 Instalação e Configuração

1. Clone o repositório ou baixe os arquivos.
2. Instale as dependências necessárias:
   ```bash
   pip install customtkinter spotipy pillow python-dotenv requests
   ```
3. Crie um arquivo `.env` na raiz do projeto com suas credenciais:
   ```env
   SPOTIPY_CLIENT_ID='seu_client_id_aqui'
   SPOTIPY_CLIENT_SECRET='seu_client_secret_aqui'
   SPOTIPY_REDIRECT_URI='http://localhost:8888/callback'
   ```

## 🏃 Como Rodar

Basta executar o arquivo principal:
```bash
python app.py
```

## 🎨 Personalização Visual

O projeto conta com:
- Janela expandida de 1050x700px.
- Foto de perfil com bordas levemente arredondadas e borda fina branca.
- Botão de logout estilizado em vermelho suave.
- Sistema de cores baseado no verde clássico do Spotify (#1DB954).

---
Desenvolvido para transformar sua experiência musical em dados visuais. 🎵

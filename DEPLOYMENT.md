# 🚀 Deployment Guide

Choose your deployment strategy: **Cloud (Render.com)** for 24/7 reliability, or **Local (Sovereign)** for 0-cost and maximum privacy.

---

## Option A: Cloud Deployment (Render.com) - *Recommended*
Best for 24/7 availability without needing your PC to be on.

### 1. Deployment Steps (Render Blueprint)
Use the included `render.yaml` for a one-click setup:
1. **Push Code**: Push this repository to a private GitHub repo.
2. **New Blueprint**: In Render, click **New > Blueprint**.
3. **Connect Repo**: Select your repository.
4. **Environment Variables**: Fill in `TELEGRAM_BOT_TOKEN`, `GOOGLE_API_KEY`, and `MASTER_KEY`.
5. **Apply**: Click "Apply" and wait for the build.

### 2. Data Persistence
Render's filesystem is ephemeral. To save data between restarts:
1. Go to **Settings > Disks** in Render.
2. Add a disk mounted at `/app/data`.
3. Set `DATABASE_URL=sqlite:////app/data/data.db` in your environment variables.

---

## Option B: Local Sovereign Hosting (0-Budget)
Best for total privacy and running local AI models (Ollama).

### 1. Local AI Setup (Ollama)
1. Install [Ollama](https://ollama.com).
2. Run `ollama pull llama3`.
3. Set `AI_PROVIDER=ollama` and `OLLAMA_BASE_URL=http://localhost:11434` in your `.env`.

### 2. Remote Access (Cloudflare Tunnel)
To access the bot/dashboard from your phone while your PC is at home:
1. Install [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/install-cloudflare-tunnel/).
2. Run: `cloudflared tunnel --url http://localhost:8501`.
3. Use the generated `.trycloudflare.com` URL to access your dashboard.

### 3. Persistent Execution
Use `screen` to keep the processes running when you close the terminal:
- `screen -S bot python3 -m src.utils.telegram_bot`
- `screen -S dashboard streamlit run src/utils/dashboard.py`

---

## 🔐 Security Best Practices
- **MASTER_KEY**: Never share this. It encrypts your Google tokens.
- **Bot Privacy**: Use `/setprivacy` in @BotFather to ensure only you can prompt the bot.
- **Environment**: Always use a `.env` file and never commit it (already handled by `.gitignore`).

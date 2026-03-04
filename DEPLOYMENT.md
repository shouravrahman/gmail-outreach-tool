# 🚀 Deployment Guide

Choose the best way to host your 24/7 AI outreach engine.

---

## 🏆 Recommended (NO Credit Card): Streamlit Community Cloud
This is the easiest, truly free way to go live today. No card, no Docker, no hassle.

### 1. Simple Steps
1. **GitHub Push**: Ensure your code is on a private GitHub repository.
2. **Sign Up**: Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
3. **Deploy App**:
   - Repository: `YOUR_REPSITORY_NAME`.
   - Branch: `master` (or `main`).
   - Main file path: `src/utils/dashboard.py`.
4. **Secrets (Crucial!)**:
   - Click **Advanced Settings** before deploying.
   - Paste your `.env` variables into the **Secrets** box in TOML format:
     ```toml
     GOOGLE_API_KEY = "xxx"
     TELEGRAM_BOT_TOKEN = "xxx"
     MASTER_KEY = "xxx"
     GOOGLE_CLIENT_JSON = '{"type": "service_account", ...}'
     ```
5. **Launch!**: Your app, telegram bot, and AI worker will all start together on a permanent `xxx.streamlit.app` URL.

---

## Alternative: Hugging Face Spaces (Truly 0-Card)
If you prefer Hugging Face, follow the steps in the [HF Guide](./DEPLOYMENT.md#alternative-local-always-on-linux--pm2). Note: Hugging Face uses Docker, so it's a bit more advanced but also 24/7 free.

---

## Local "Always On" (Linux / PM2)
If you want to keep everything on your own machine but act like a pro server:
1. `sudo npm install pm2 -g`
2. `pm2 start scripts/run_prod.sh --name outreach-agent`
3. `pm2 save && pm2 startup`
This keeps everything running 24/7 on your PC without any external credit card or cloud limits.

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

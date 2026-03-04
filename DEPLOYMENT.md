# 🚀 Deployment Guide

Get your 24/7 sustainable URL without any credit card barriers using **Hugging Face Spaces**.

---

## 🏆 Recommended: Hugging Face Spaces (Truly 0-Card)
Hugging Face is the most reliable platform to host Docker-based apps for free without ever asking for a credit card.

### 1. Simple Steps
1. **GitHub Push**: Ensure your code is on a private GitHub repo.
2. **Sign Up**: Create an account at [Hugging Face](https://huggingface.co/join).
3. **New Space**:
   - Go to [huggingface.co/new-space](https://huggingface.co/new-space).
   - **Space Name**: e.g., `outreach-agent`.
   - **Space SDK**: Select **Docker**.
   - **Docker Template**: Select **Blank**.
   - **Visibility**: **Private** (Recommended for your safety).
4. **Connect GitHub**:
   - Go to the **Settings** tab of your new Space.
   - Click "Connect a GitHub repository" and select this repo.
5. **Add Secrets (Environment Variables)**:
   - Still in **Settings**, scroll to **Variables and secrets**.
   - Add the following as **Secrets** (not Variables):
     - `GOOGLE_API_KEY`
     - `TELEGRAM_BOT_TOKEN`
     - `MASTER_KEY`
     - `GOOGLE_CLIENT_JSON` (Paste the whole JSON string)
6. **Port Verification**: 
   - Ensure the `README.md` on Hugging Face (the metadata block) has `app_port: 8501`. (The Space will try to use 7860 by default).

---

## 🛠️ Performance & Maintenance
Since Hugging Face's free tier is 24/7 but has limited RAM:
- **Auto-Restart**: If the app crashes, Hugging Face will restart it automatically.
- **Persistence**: Note that `data.db` will be reset on restarts. For permanent data, you should use the [Hugging Face Datasets](https://huggingface.co/docs/hub/datasets) or an external database like MongoDB Atlas (Free Tier available).

---

## Local "Always On" (Linux / PM2)
If you prefer to keep everything on your machine:
1. `sudo npm install pm2 -g`
2. `pm2 start scripts/run_prod.sh --name outreach-agent`
3. `pm2 save && pm2 startup`
This ensures if your machine restarts, the bot and dashboard come back up automatically without any credit card.

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

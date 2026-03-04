# 🛡️ 0-Budget Secured Deployment (Sovereign Hosting)

Since most "Free" VPS providers require credit cards, the most secure and cost-effective way to run this agent is **Sovereign Hosting**: running it on your own local hardware (or an old laptop) and exposing the monitor safely via **Cloudflare Tunnels**.

## 1. Local AI Configuration (Ollama)
For a 100% private, 0-cost setup, use Ollama:
1. **Install**: [Ollama.com](https://ollama.com/)
2. **Download Model**: `ollama pull llama3` (or `mistral`, `phi3`).
3. **Start Server**: Ensure the Ollama app is running or run `ollama serve`.

## 2. Secure Remote Access (Cloudflare Tunnel)
You can access your Streamlit dashboard from anywhere without opening router ports or paying for a static IP.
1. **Install Cloudflared**:
   ```bash
   curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
   chmod +x cloudflared
   ```
2. **Launch Quick Tunnel**:
   ```bash
   ./cloudflared tunnel --url http://localhost:8501
   ```
3. **Save the Link**: Cloudflare will generate a random URL (e.g., `https://random-words.trycloudflare.com`). **Bookmark this link**—it's your private gateway to your outreach monitor.

## 3. Persistent Process Management
To keep the agent running even after you close your terminal:

### Option A: Using `screen` (Easiest)
1. Start a session: `screen -S outreach`
2. Run the bot: `python3 -m src.utils.telegram_bot`
3. **Detach**: Press `Ctrl+A`, then `D`.
4. **Re-attach**: `screen -r outreach`

---

## 🔐 Security Best Practices

- **MASTER_KEY**: This is the heart of your security. If anyone gets this key AND your `data.db`, they can access your Gmail tokens. Keep it in your `.env` and never share it.
- **Client JSON**: The `GOOGLE_CLIENT_JSON` contains your API secrets. Ensure your `.env` file is excluded from git (check `.gitignore`).
- **Bot Privacy**: Use Telegram's Bot Settings to disable "Allow Groups" so nobody can add your bot to a shared group and see your outreach data.

## 🚀 Why this setup?
- **Zero Cost**: No monthly VPS bills.
- **Privacy**: Your leads and tokens never leave your physical hardware.
- **Bypass Censorship**: Cloud AI models can sometimes refuse to write certain outreach; local models (Ollama) will follow your instructions 100%.

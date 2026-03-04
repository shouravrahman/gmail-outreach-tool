# AI Outreach Agent 🚀

A sophisticated, Telegram-controlled AI agent for personalized email outreach. It automates lead processing from Google Sheets and sends emails via Gmail using LangGraph for stateful workflows.

## ✨ Key Features
- **Telegram Interface**: Command your agent, connect accounts, and approve drafts from your phone.
- **Multi-Model AI**: Seamlessly switch between **Gemini**, **OpenAI**, and **Ollama (Local)**.
- **Human-in-the-Loop**: Preview and approve every AI-generated draft before it's sent.
- **Sovereign & Secure**: Local SQLite storage with **AES-256 encryption** for your Google tokens.
- **Real-time Monitoring**: Visual dashboard built with Streamlit to track campaign progress.
- **Safety Boundaries**: Built-in "Wait" nodes with jitter to simulate human behavior and protect account health.

---

## 🛠️ Step 1: Prerequisites

1. **Google Cloud Console**:
   - Create a project and enable **Gmail API** and **Google Sheets API**.
   - Create **OAuth 2.0 Credentials** (Web Application).
   - Add Authorized Redirect URI: `http://localhost:3001/api/auth/callback`
   - Download the `client_secret.json`.
2. **Telegram**:
   - Create a bot via [@BotFather](https://t.me/BotFather) and save the token.
3. **Local AI (Optional)**:
   - Install [Ollama](https://ollama.com/) if you want to run models locally (e.g., Llama 3).

---

## 🚀 Step 2: Setup & Installation

1. **Clone & Install**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Configure Environment**:
   - Copy `.env.example` to `.env`.
   - **MASTER_KEY**: Generate a long random string. This secures your Google tokens.
   - **GOOGLE_CLIENT_JSON**: Open your `client_secret.json` and paste the entire JSON content as a single line.
   - **TELEGRAM_BOT_TOKEN**: Paste your token from BotFather.
   - **AI_PROVIDER**: Set to `gemini`, `openai`, or `ollama`.

---

## 📱 Step 3: The "Always-on" Sync (Crucial for Mobile)
To use the bot from your mobile while the agent runs on your PC, you need a **Public Tunnel**. This solves the `localhost` issue.

1.  **Install Cloudflare Tunnel**: follow [these steps](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/install-cloudflare-tunnel/).
2.  **Start the Tunnel**:
    ```bash
    cloudflared tunnel --url http://localhost:8501
    ```
3.  **Update Google Redirect**: Use the generated `.trycloudflare.com` URL in your Google Console and `.env` instead of `localhost:3001`. Now, when you authorize on mobile, it will redirect back to your PC correctly!

---

## 🎮 Step 4: Running the Agent

Open three terminals (venv activated):

**1. The Assistant Bot** (Telegram interface)
```bash
python3 -m src.utils.telegram_bot
```

**2. The Background Worker** (The "Brain" that drafts/sends)
```bash
python3 -m src.agent.worker
```

**3. The Pro Dashboard** (Visual control & editing)
```bash
streamlit run src/utils/dashboard.py
```

---

## 📖 Step 4: Usage Guide

1. **Link Gmail**: In Telegram, send `/connect`. Click the link, authorize, and paste the resulting code back to the bot.
2. **Start Campaign**: Send `/campaign`. The bot will guide you through:
   - Naming the campaign.
   - Providing your Google Sheet URL.
   - Setting the AI's goal (the "Prompt").
   - Choosing the AI provider.
3. **Review & Approve**: The agent will process your leads and send you drafts in Telegram. Click **Approve** to send or **Reject** to skip.
4. **Monitor**: Watch the Streamlit dashboard for a live feed of sent emails and campaign status.

---

## 🛡️ Deployment & Advanced Security
For 0-budget hosting and advanced security setups, see [DEPLOYMENT.md](./DEPLOYMENT.md).

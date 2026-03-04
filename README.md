# AI Outreach Agent 🚀

A sophisticated, Telegram-controlled AI agent for personalized email outreach. It automates lead processing from Google Sheets and sends emails via Gmail or Resend using LangGraph for stateful workflows.

## ✨ Key Features
- **Telegram Interface**: Command your agent, connect accounts, and approve drafts from your phone.
- **Multi-Model AI**: Support for **Gemini**, **OpenAI**, and **Ollama (Local)**.
- **Human-in-the-Loop**: Preview and approve every AI-generated draft before it's sent.
- **Flexible Hosting**: Run 24/7 on **Render.com** or locally on your own hardware.

---

## 🚀 Deployment Options

### 1. Cloud (Render.com)
Deploy in minutes with one-click Blueprint support. Ideal for 24/7 availability.
- See [DEPLOYMENT.md](./DEPLOYMENT.md#option-a-cloud-deployment-rendercom---recommended) for steps.

### 2. Local (Ollama + Tunnels)
Run 100% private and 0-cost using local AI models and Cloudflare Tunnels.
- See [DEPLOYMENT.md](./DEPLOYMENT.md#option-b-local-sovereign-hosting-0-budget) for steps.

---

## 🛠️ Local Development Setup

1. **Clone & Install**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Configure Environment**:
   - Copy `.env.example` to `.env`.
   - Fill in your `MASTER_KEY`, `GOOGLE_CLIENT_JSON`, and `TELEGRAM_BOT_TOKEN`.
3. **Run Services**:
   - **Telegram Bot**: `python3 -m src.utils.telegram_bot`
   - **Streamlit Dashboard**: `streamlit run src/utils/dashboard.py`

---

## 🎮 Usage Guide
1. **Link Gmail**: Send `/connect` in Telegram.
2. **Start Campaign**: Send `/campaign` to set your target sheet and AI goal.
3. **Approve Drafts**: Review AI-generated emails in Telegram or the Dashboard.
4. **Scale**: Watch your leads turn into conversations!

---

## 🛡️ Security & Privacy
Your leads and tokens are encrypted with AES-256 and stored in your private database.

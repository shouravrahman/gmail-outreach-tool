---
title: Outreach Agent
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# AI Outreach Agent 🚀

A sophisticated, Telegram-controlled AI agent for personalized email outreach. It automates lead processing from Google Sheets and sends emails via Gmail or Resend using LangGraph for stateful workflows.

## ✨ Key Features
- **Telegram Interface**: Command your agent, connect accounts, and approve drafts from your phone.
- **Multi-Model AI**: Support for **Gemini**, **OpenAI**, and **Ollama (Local)**.
- **Human-in-the-Loop**: Preview and approve every AI-generated draft before it's sent.
- **Flexible Hosting**: Run 24/7 on **Hugging Face Spaces** or locally on your own hardware.

---

## 🚀 Deployment Options

### 1. Cloud (Hugging Face Spaces) - 0-Card Required
Deploy 24/7 for free without a credit card.
- See [DEPLOYMENT.md](./DEPLOYMENT.md#-recommended-hugging-face-spaces-truly-0-card) for steps.

### 2. Local (Sovereign Hosting)
Run 100% private using local AI and your own hardware.
- See [DEPLOYMENT.md](./DEPLOYMENT.md#local-always-on-linux--pm2) for steps.

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

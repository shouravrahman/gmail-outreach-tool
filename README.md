# Bulk Email Tool 📧

A production-grade bulk email system with NLU, approval workflows, and security hardening. Designed for easy deployment on Streamlit Cloud.

## Features

- 🔐 **Enterprise Security** - PBKDF2-SHA256 encryption, JWT auth, rate limiting, input validation
- 🧠 **Natural Language** - Intent classification, entity extraction, semantic search
- 👥 **Approval Workflows** - Campaign approvals, role-based access (Admin/Manager/User/Viewer)
- 📊 **Beautiful Dashboard** - Streamlit UI with analytics, templates, audit logs
- 📨 **Email Management** - Create campaigns, manage templates, track recipients
- 🔍 **Audit Trails** - Full action logging for compliance

## Quick Start

**Local Development**
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create secrets file
cp .env.example .env

# Run locally
streamlit run app.py
```

Open http://localhost:8501

## 🚀 Deploy to Streamlit Cloud

This application is optimized for Streamlit Cloud's free tier. It runs the Dashboard, AI Worker, and Telegram Bot in a single process.

### Setup Steps:
1. **Prepare your database:**
   - Create a NeonDB project at [console.neon.tech](https://console.neon.tech)
   - Copy your PostgreSQL connection string
   - See [NEONDB_SETUP.md](NEONDB_SETUP.md) for details

2. **Push to GitHub:**
   ```bash
   git add -A
   git commit -m "Ready for deployment"
   git push origin main
   ```

3. **Deploy:**
   - Go to [streamlit.io/cloud](https://streamlit.io/cloud)
   - Click "New app" → Connect GitHub repo
   - Select branch and `app.py` as main file
   - Click "Deploy"

4. **Add Secrets:**
   - Click **Advanced settings** → **Secrets**
   - Add these secrets (copy from `.streamlit/secrets.example.toml`):
   ```
   DATABASE_URL="postgresql://user:pass@host/bulk_email?sslmode=require"
   MASTER_KEY="your-random-32-char-key"
   ENCRYPTION_SALT="your-random-salt"
   JWT_SECRET="your-random-jwt-secret"
   TELEGRAM_BOT_TOKEN="optional-bot-token"
   TELEGRAM_CHAT_ID="optional-chat-id"
   ```
   - Click "Save"

5. **Auto-Deploy:**
   - Your app will deploy automatically
   - Every git push redeploys instantly
   - Check deployment status in Streamlit Cloud dashboard

### Optional: Add Error Notifications
To get Telegram alerts for critical errors:
- Get a bot token: [@BotFather](https://t.me/botfather)
- Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to secrets

---

## 🎮 Usage Guide (Dashboard)
1. **Register**: Create account in Streamlit dashboard
2. **Create Campaign**: Add email, recipients, template
3. **Approve**: Manager approves campaign before sending
4. **Monitor**: View analytics and delivery status
5. **Audit**: Check action history

**NLU Commands** (Natural Language):
- "Send emails to all @gmail.com users"
- "Filter recipients by domain"
- "Show campaigns from Q1"
- "Approve marketing campaign"

---

## 🛡️ Security & Privacy
- All data encrypted with PBKDF2-SHA256 and Fernet encryption
- Stored in your private SQLite/PostgreSQL database
- 100% action logging for compliance
- Role-based access control
- Rate limiting to prevent abuse

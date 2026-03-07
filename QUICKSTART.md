# Quick Start

## Fastest Way to Run

```bash
chmod +x run.sh
./run.sh
```

This automatically:
- ✅ Creates virtual environment (if needed)
- ✅ Activates it
- ✅ Starts Streamlit app
- Open: http://localhost:8501

## Manual Setup (if not using run.sh)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create secrets file
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your values

# Run
streamlit run app.py
```

## Secrets Configuration

Create `.streamlit/secrets.toml`:
```toml
# Required
MASTER_KEY="your-random-32-char-key"
ENCRYPTION_SALT="your-random-salt"
JWT_SECRET="your-random-jwt-secret"

# Database (PostgreSQL recommended)
DATABASE_URL="postgresql://user:pass@host/bulk_email?sslmode=require"

# Optional: Telegram alerts
TELEGRAM_BOT_TOKEN="your-bot-token"
TELEGRAM_CHAT_ID="your-chat-id"
```

**Generate secure keys:**
```bash
python3 -c "import secrets; print(secrets.token_hex(16))"
```

## Deploy to Streamlit Cloud

1. Push to GitHub:
   ```bash
   git push origin main
   ```

2. Go to https://streamlit.io/cloud

3. Click "New app" → select repo and `app.py`

4. Add secrets (same as `.streamlit/secrets.toml`)

5. Deploy!

**That's it!** Auto-deploys on every `git push`

## Next Steps

- See [NEONDB_SETUP.md](NEONDB_SETUP.md) for database setup
- See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment guide

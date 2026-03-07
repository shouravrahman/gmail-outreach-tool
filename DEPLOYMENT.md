# 🚀 Deployment Guide

This application is designed for **Streamlit Cloud** (Monolithic Architecture). This allows you to run the Dashboard, AI Worker, and Telegram Bot all on the free tier without complex infrastructure.

---

## Why Streamlit Cloud?
- ✅ Free tier is generous (4 apps)
- ✅ One-click deploy from GitHub
- ✅ Auto-deploys on every push
- ✅ No config files needed
- ✅ Perfect for open source projects

## Deploy Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Ready for Streamlit Cloud"
   git push origin master
   ```

2. **Go to Streamlit Cloud**
   Visit: https://streamlit.io/cloud

3. **Create New App**
   - Select your GitHub account
   - Select repository: `bulk-email-tool`
   - Select branch: `master`
   - Select main file: `app.py`

4. **Configure Secrets**
   Click "Advanced settings" → "Secrets". Copy the contents of `.env.example` (or `.streamlit/secrets.example.toml`) and fill in your values.

   ```
   MASTER_KEY="your-secure-random-key-32-chars"
   ENCRYPTION_SALT="your-secure-random-salt"
   JWT_SECRET="your-secure-random-secret"
   DATABASE_URL="postgresql://..."
   # ... add other secrets
   ```

5. **Deploy**
   Click "Deploy". Your app will be live at `https://[your-app-name].streamlit.app`.

---

## Database Setup (NeonDB / PostgreSQL)

We recommend a cloud PostgreSQL database like **NeonDB**.
1. Create NeonDB project: https://console.neon.tech
2. Copy connection string.
3. Set `DATABASE_URL` in your deployment secrets.

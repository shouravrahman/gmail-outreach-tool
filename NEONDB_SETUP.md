# NeonDB Setup Guide

This app is configured to use **NeonDB** (PostgreSQL) for production data persistence.

## 1. Create a NeonDB Project

1. Go to [console.neon.tech](https://console.neon.tech)
2. Sign up with GitHub or email
3. Create a new project:
   - **Name**: `bulk-email-tool`
   - **Database**: `bulk_email` (will be created)
   - **Region**: Choose closest to your Streamlit Cloud region (US-East-4 recommended)

## 2. Get Your Connection String

1. In Neon Console, click **Connection string**
2. Copy the **PostgreSQL** connection string
3. It should look like:
   ```
   postgresql://user:password@ep-xyz.us-east-4.aws.neon.tech/bulk_email?sslmode=require
   ```

## 3. Local Development Setup

### Option A: Using .streamlit/secrets.toml (Recommended)

1. Create `.streamlit/secrets.toml` in your project root:
   ```bash
   cp .streamlit/secrets.example.toml .streamlit/secrets.toml
   ```

2. Open `.streamlit/secrets.toml` and replace:
   ```toml
   DATABASE_URL = "postgresql://user:password@ep-xyz.us-east-4.aws.neon.tech/bulk_email?sslmode=require"
   ```

3. Run locally:
   ```bash
   ./run.sh
   ```
   Or:
   ```bash
   source venv/bin/activate
   streamlit run app.py
   ```

### Option B: Environment Variable

```bash
export DATABASE_URL="postgresql://user:password@ep-xyz.us-east-4.aws.neon.tech/bulk_email?sslmode=require"
streamlit run app.py
```

## 4. Streamlit Cloud Deployment

1. **Add Secret to Streamlit Cloud**:
   - Go to your app settings
   - Click **Advanced settings** → **Secrets**
   - Paste your NeonDB connection string:
     ```
     DATABASE_URL = "postgresql://user:password@ep-xyz.us-east-4.aws.neon.tech/bulk_email?sslmode=require"
     ```

2. **Push to GitHub**:
   ```bash
   git add -A
   git commit -m "Add NeonDB support"
   git push origin main
   ```

3. **Deploy** - Streamlit Cloud auto-deploys on push
   - Your app will automatically connect to NeonDB
   - All data persists across deployments

## 5. Verify Connection

The app will log on startup:
```
Using PostgreSQL database: ep-xyz.us-east-4.aws.neon.tech
```

If you see:
```
Using SQLite for local development
```

Then `DATABASE_URL` is not set - check your secrets!

## 6. Database Management

### Backup Your Data

NeonDB automatically backs up every branch. To manually export:

```bash
pg_dump "postgresql://user:password@ep-xyz.us-east-4.aws.neon.tech/bulk_email?sslmode=require" > backup.sql
```

### View Database in Neon Console

1. Go to [console.neon.tech](https://console.neon.tech)
2. Select your project
3. Click **SQL Editor** to run queries
4. Or use CLI:
   ```bash
   psql "postgresql://user:password@ep-xyz.us-east-4.aws.neon.tech/bulk_email?sslmode=require"
   ```

## 7. Troubleshooting

### Connection Refused
- Check if your IP is whitelisted in Neon (usually automatic)
- Verify `DATABASE_URL` in secrets is correct
- Make sure `?sslmode=require` is included

### Table Not Found
- First run will auto-create all tables
- Check logs in Streamlit Cloud: **Manage app** → **Logs**

### Slow Queries
- NeonDB includes monitoring in console
- Check active connections and query performance

## 8. Cost

**NeonDB Free Tier Includes**:
- Up to 3 projects
- 3 GB storage
- 20 GB egress/month
- Full PostgreSQL features

**Paid**: Pay as you go (~$0.16/GB storage, $0.20/GB egress)

Perfect for a bulk email tool!

---

**Next Steps:**
1. Create NeonDB project
2. Copy connection string
3. Add to `.streamlit/secrets.toml` or Streamlit Cloud secrets
4. Run: `./run.sh` or `streamlit run app.py`
5. Verify database is being used (check logs)

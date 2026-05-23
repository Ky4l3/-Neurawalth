# Deploy Strove Leads — Free Hosting

## Option 1: Railway (Recommended — 5 minutes)

Railway has the easiest setup and reliable persistent storage.

### Steps

1. Go to **[railway.app](https://railway.app)** → sign up with GitHub
2. Click **New Project → Deploy from GitHub repo**
3. Pick your `-Neurawalth` repo, branch `claude/strove-leads-scraper-H6IWl`
4. In service settings:
   - **Root directory:** `strove_leads`
   - **Build:** `pip install -r requirements.txt && playwright install chromium`
   - **Start:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
5. Click **Variables** → add:
   - `SECRET_KEY` (click "Generate" or any random string)
   - `DB_PATH=/data/strove_leads.db`
   - `SERP_API_KEY` (optional, paste from SerpAPI)
   - `HUNTER_API_KEY` (optional)
6. Click **Volumes → Add Volume** → mount path `/data`, size 1GB
7. Click **Settings → Networking → Generate Domain**
8. Done — your dashboard is live at `https://<your-app>.up.railway.app`

**Cost:** Free tier gives $5/month credit. App uses ~$3/month idle. Effectively free.

---

## Option 2: Render (Free tier, sleeps after 15 min idle)

1. Go to **[render.com](https://render.com)** → sign up with GitHub
2. **New → Web Service** → connect repo
3. Choose **branch:** `claude/strove-leads-scraper-H6IWl`
4. Settings:
   - **Root directory:** `strove_leads`
   - **Runtime:** Python 3
   - **Build:** `pip install -r requirements.txt && playwright install chromium --with-deps`
   - **Start:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
   - **Plan:** Free
5. **Advanced → Add Disk:** Name `data`, mount `/data`, 1GB
6. **Environment Variables:**
   - `DB_PATH=/data/strove_leads.db`
   - `SECRET_KEY=<random string>`
   - `PYTHON_VERSION=3.11.9`
7. Click **Create Web Service**

⚠ **Free tier caveat:** Render free tier spins down after 15min of no traffic. Your scheduled scrape may miss its 6am window. Upgrade to $7/mo or use Railway instead if scheduling matters.

---

## Option 3: Local + Cloudflare Tunnel (Always-on from your laptop)

Run on your own machine, expose via Cloudflare:

```bash
# Terminal 1: run the app
cd strove_leads && python app.py

# Terminal 2: expose via Cloudflare tunnel (free, no signup)
# Install: brew install cloudflared  (or https://github.com/cloudflare/cloudflared/releases)
cloudflared tunnel --url http://localhost:5000
```

Cloudflare gives you a free public URL. Good for testing but your laptop must stay on.

---

## Why Not Vercel?

You asked about Vercel — it doesn't support persistent SQLite (filesystem is ephemeral, resets on every deploy). It also doesn't run APScheduler well (functions are stateless). Use Railway or Render.

---

## Post-Deploy Checklist

After deploy:

1. Visit `https://<your-app>/` — should load the dashboard
2. Visit `/settings` → add API keys via the UI (or set as env vars)
3. Click **Start Scrape Now** on the dashboard — watch the progress bar
4. Wait 3–5 minutes — check `/leads` for results
5. Set the schedule on `/settings` (default 6am UTC)

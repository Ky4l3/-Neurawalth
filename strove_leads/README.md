# Strove Leads

Automated outbound lead scraper for Strove — finds 200+ high-ticket coaching leads daily from Google, LinkedIn, Instagram, and coaching directories.

## Quick Start (Local)

### 1. Prerequisites
- Python 3.11+
- pip

### 2. Install dependencies

```bash
cd strove_leads
pip install -r requirements.txt
playwright install chromium --with-deps
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY
```

### 4. Run

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## Deployment

### Option A — Railway (Recommended, Free Tier Available)

1. Create account at [railway.app](https://railway.app)
2. Click **New Project → Deploy from GitHub repo**
3. Point to your repo, set **Root Directory** to `strove_leads`
4. Add environment variables from `.env.example`
5. Railway auto-detects the `Procfile` and deploys

**Persistent storage:** Railway free tier has ephemeral storage. Add a Volume in the Railway dashboard and set `DB_PATH=/data/strove_leads.db`.

### Option B — Render (Free Tier)

1. Create account at [render.com](https://render.com)
2. New → **Web Service** → connect GitHub repo
3. Set **Root Directory** to `strove_leads`
4. Build command: `pip install -r requirements.txt && playwright install chromium --with-deps`
5. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
6. Add a **Disk** (1GB) mounted at `/data`
7. Set env var `DB_PATH=/data/strove_leads.db`

### Option C — PythonAnywhere (Free)

1. Create account at [pythonanywhere.com](https://pythonanywhere.com)
2. Upload or clone your repo
3. Create a virtual environment and install requirements
4. Configure as a WSGI app pointing to `app:app`
5. Note: Playwright may not work on PythonAnywhere free tier — scraping will fall back to requests-based scrapers

### Option D — VPS (DigitalOcean/Hetzner)

```bash
# On your server
git clone <your-repo>
cd strove_leads
pip install -r requirements.txt
playwright install chromium --with-deps

# Run with gunicorn
gunicorn app:app --bind 0.0.0.0:5000 --workers 1 --threads 4 --daemon

# Or use systemd service for auto-restart
```

---

## API Keys (Optional but Recommended)

| Key | Provider | Purpose | Cost |
|-----|----------|---------|------|
| `SERP_API_KEY` | [serpapi.com](https://serpapi.com) | Reliable Google results | $50/mo (100 searches free/mo) |
| `HUNTER_API_KEY` | [hunter.io](https://hunter.io) | Email discovery | Free tier: 25/mo |
| `SNOV_API_KEY` | [snov.io](https://snov.io) | Email discovery | Free tier: 50/mo |

The app works **without** any API keys using DuckDuckGo scraping as fallback. API keys significantly improve coverage and reliability.

---

## How It Works

### Sources

| Source | Method | Leads/Day |
|--------|--------|-----------|
| Google/DuckDuckGo | Searches `"business coach" site:instagram.com` etc. | 50+ |
| Directories | Scrapes Noomii, Coach.me, Bark, TheCoachingDirectory | 80+ |
| LinkedIn | Public search pages + DuckDuckGo LinkedIn queries | 50+ |
| Instagram | Hashtag pages (#businesscoach etc.) + Google search | 30+ |

### Qualification Rules

A lead is only saved if it scores ≥ 3/10 and passes all these checks:
- ✅ Bio mentions coach/consultant/mentor
- ✅ Has a website, LinkedIn, or Instagram handle
- ✅ Located in US, UK, Canada, or Australia
- ✅ Shows high-ticket signals (apply, program, VIP, etc.)
- ❌ Skipped if bio mentions "marketing agency" / "full marketing team"
- ❌ Skipped if no contact info at all

### Anti-Blocking

- Rotates 7 different User-Agent strings
- Random 2–5 second delays between requests
- Retry failed requests up to 3 times
- Graceful handling when blocked (logs and continues)

---

## Dashboard Pages

| Page | URL | Purpose |
|------|-----|---------|
| Dashboard | `/` | Stats, scrape control, countdown timer |
| Leads | `/leads` | Searchable table with filters and bulk actions |
| Export | `/export` | CSV, Apollo, HubSpot export |
| Settings | `/settings` | API keys, schedule, queries, countries |

---

## Database

SQLite at `strove_leads.db` (or `DB_PATH` env var).

### Lead Statuses
- **New** — just scraped
- **Contacted** — outreach sent
- **Replied** — they responded
- **Call Booked** — discovery call scheduled
- **Closed** — became a client
- **Not Qualified** — disqualified

---

## Troubleshooting

**Playwright won't install:**
```bash
playwright install chromium --with-deps
# If that fails:
pip install playwright && python -m playwright install
```

**No leads found:**
- Check scrape logs on the Dashboard
- Try running with just `directories` source first (most reliable)
- Add a SerpAPI key for better Google coverage

**Database locked error:**
- Only one gunicorn worker is supported (SQLite limitation)
- Ensure `--workers 1` in the start command

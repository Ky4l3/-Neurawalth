# API Keys — How To Get Them

You can run Strove Leads **without any API keys** (it falls back to DuckDuckGo scraping), but adding these will significantly boost your daily lead count.

## TL;DR — Just want it working fast?

Get **SerpAPI** only. 100 free Google searches/month = ~50 leads/day from Google alone. Skip the rest until you need them.

---

## 1. SerpAPI — Google Search (Most Important)

**Free tier:** 100 searches/month. Each scrape uses ~10 searches.

1. Go to **[serpapi.com/users/sign_up](https://serpapi.com/users/sign_up)**
2. Sign up with email (no credit card required for free tier)
3. Verify your email
4. Go to **[serpapi.com/manage-api-key](https://serpapi.com/manage-api-key)**
5. Copy the API key
6. Paste it in:
   - Either the dashboard at `/settings` → SerpAPI Key
   - Or in `.env` file: `SERP_API_KEY=your_key_here`

## 2. Hunter.io — Email Discovery

**Free tier:** 25 email lookups/month + 50 email verifications.

1. Go to **[hunter.io/users/sign_up](https://hunter.io/users/sign_up)**
2. Sign up (free, no credit card)
3. Verify email
4. Go to **[hunter.io/api-keys](https://hunter.io/api-keys)**
5. Copy your API key
6. Paste in `/settings` or `.env`: `HUNTER_API_KEY=your_key_here`

## 3. Snov.io — Alternative Email Finder

**Free tier:** 50 credits/month.

1. Go to **[snov.io/register](https://app.snov.io/register)**
2. Sign up
3. Go to **[Settings → API](https://app.snov.io/account#/api)**
4. Copy your **User ID** and **API Secret**
5. Paste in `/settings` or `.env`: `SNOV_API_KEY=user_id:secret`

---

## Validating Your Keys

After adding keys, run:

```bash
python test_apis.py
```

You'll see ✓ for each working key, ⊘ for unconfigured, ✗ for invalid.

---

## Without Any Keys — What You Get

- ✓ All 4 directory scrapers (Noomii, Coach.me, Bark, TheCoachingDirectory)
- ✓ Instagram hashtag scraping via Playwright
- ✓ LinkedIn public search scraping
- ✓ DuckDuckGo fallback for Google queries (slightly lower volume)
- ✗ No automatic email finding from domains

Expected daily volume **without keys**: 80–150 leads
Expected daily volume **with SerpAPI**: 150–250 leads
Expected daily volume **with all 3 keys**: 200–350 leads

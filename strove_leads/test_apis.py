"""Validate API keys are working. Run: python test_apis.py"""
import os
import sys
from pathlib import Path

# Load .env
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())

import requests

GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'


def test_serpapi():
    key = os.environ.get('SERP_API_KEY', '').strip()
    if not key:
        print(f"{YELLOW}⊘  SerpAPI — not configured{NC}")
        return
    try:
        r = requests.get('https://serpapi.com/account', params={'api_key': key}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            left = data.get('plan_searches_left', '?')
            print(f"{GREEN}✓  SerpAPI — working, {left} searches left{NC}")
        else:
            print(f"{RED}✗  SerpAPI — invalid key ({r.status_code}){NC}")
    except Exception as e:
        print(f"{RED}✗  SerpAPI — error: {e}{NC}")


def test_hunter():
    key = os.environ.get('HUNTER_API_KEY', '').strip()
    if not key:
        print(f"{YELLOW}⊘  Hunter.io — not configured{NC}")
        return
    try:
        r = requests.get(
            'https://api.hunter.io/v2/account',
            params={'api_key': key},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json().get('data', {})
            used = data.get('requests', {}).get('searches', {}).get('used', '?')
            avail = data.get('requests', {}).get('searches', {}).get('available', '?')
            print(f"{GREEN}✓  Hunter.io — working, {used}/{avail} searches used{NC}")
        else:
            print(f"{RED}✗  Hunter.io — invalid key ({r.status_code}){NC}")
    except Exception as e:
        print(f"{RED}✗  Hunter.io — error: {e}{NC}")


def test_snov():
    key = os.environ.get('SNOV_API_KEY', '').strip()
    if not key:
        print(f"{YELLOW}⊘  Snov.io — not configured{NC}")
        return
    # Snov.io uses client_id/secret OAuth; this just checks the key is present
    print(f"{YELLOW}⊘  Snov.io — present but uses OAuth (test by running a scrape){NC}")


def test_db():
    try:
        from database.db import get_dashboard_stats
        stats = get_dashboard_stats()
        print(f"{GREEN}✓  Database — {stats['total_leads']} leads stored{NC}")
    except Exception as e:
        print(f"{RED}✗  Database — error: {e}{NC}")


def test_playwright():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        print(f"{GREEN}✓  Playwright — Chromium ready{NC}")
    except Exception as e:
        print(f"{YELLOW}⊘  Playwright — {str(e)[:60]} (will fall back to requests){NC}")


if __name__ == '__main__':
    print("\n━━━ Strove Leads — System Check ━━━\n")
    test_db()
    test_playwright()
    print()
    test_serpapi()
    test_hunter()
    test_snov()
    print()
    print(f"Run {GREEN}python app.py{NC} to start the dashboard at http://localhost:5000\n")

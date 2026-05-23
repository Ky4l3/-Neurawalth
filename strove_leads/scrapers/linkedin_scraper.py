import logging
import re
import json
import os
import requests
from typing import List
from .base_scraper import (
    get_headers, random_delay, detect_country, detect_niche,
    qualify_lead, extract_email_from_text, extract_website_from_text,
    is_coaching_profile
)

logger = logging.getLogger(__name__)

LINKEDIN_SEARCHES = [
    ('business coach', 'US'),
    ('executive coach', 'US'),
    ('life coach', 'US'),
    ('business coach', 'UK'),
    ('executive coach', 'UK'),
    ('business coach', 'CA'),
    ('business coach', 'AU'),
    ('mindset coach', 'US'),
    ('leadership coach', 'US'),
    ('high ticket coach', 'US'),
]

COUNTRY_CODES = {
    'US': '103644278',
    'UK': '101165590',
    'CA': '101452733',
    'AU': '101452733',
}


def scrape_linkedin_source(hunter_api_key: str = None) -> List[dict]:
    leads = []

    # Try Playwright-based scraping first
    try:
        from playwright.sync_api import sync_playwright
        leads = _scrape_linkedin_playwright(hunter_api_key)
    except ImportError:
        logger.warning("Playwright not available, using requests-based LinkedIn scraping")
        leads = _scrape_linkedin_requests(hunter_api_key)
    except Exception as e:
        logger.error(f"Playwright LinkedIn scrape failed: {e}")
        leads = _scrape_linkedin_requests(hunter_api_key)

    return leads


def _scrape_linkedin_playwright(hunter_api_key: str = None) -> List[dict]:
    from playwright.sync_api import sync_playwright
    leads = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
            ]
        )

        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='en-US',
        )
        context.set_extra_http_headers({'Accept-Language': 'en-US,en;q=0.9'})
        page = context.new_page()

        for search_term, country in LINKEDIN_SEARCHES[:5]:
            try:
                search_url = f'https://www.linkedin.com/search/results/people/?keywords={search_term.replace(" ", "%20")}&origin=GLOBAL_SEARCH_HEADER'
                page.goto(search_url, wait_until='domcontentloaded', timeout=20000)
                random_delay(3, 5)

                # Check if login wall appeared
                if 'login' in page.url or 'authwall' in page.url:
                    logger.info("LinkedIn requires login, extracting from search snippets")
                    content = page.content()
                    extracted = _parse_linkedin_html(content, search_term, country)
                    leads.extend(extracted)
                    continue

                content = page.content()
                extracted = _parse_linkedin_html(content, search_term, country)
                leads.extend(extracted)

                random_delay(4, 8)

            except Exception as e:
                logger.error(f"LinkedIn Playwright error for '{search_term}': {e}")

        browser.close()

    return leads


def _scrape_linkedin_requests(hunter_api_key: str = None) -> List[dict]:
    """Requests-based fallback — scrapes LinkedIn public search pages."""
    leads = []
    session = requests.Session()

    for search_term, country in LINKEDIN_SEARCHES[:8]:
        try:
            url = f'https://www.linkedin.com/pub/dir/?firstName=&lastName=&search=Search&keywords={search_term.replace(" ", "+")}'
            resp = session.get(url, headers=get_headers('https://www.linkedin.com/'), timeout=15)

            if resp.status_code == 200:
                extracted = _parse_linkedin_html(resp.text, search_term, country)
                leads.extend(extracted)

            random_delay(3, 6)

        except Exception as e:
            logger.error(f"LinkedIn requests error for '{search_term}': {e}")

    # Also try Google search for LinkedIn profiles
    google_leads = _google_linkedin_search(session)
    leads.extend(google_leads)

    return leads


def _google_linkedin_search(session: requests.Session) -> List[dict]:
    """Use DuckDuckGo to find LinkedIn profiles."""
    leads = []
    queries = [
        'site:linkedin.com/in "business coach" "United States"',
        'site:linkedin.com/in "executive coach" "United Kingdom"',
        'site:linkedin.com/in "life coach" "Canada" OR "Australia"',
        'site:linkedin.com/in "mindset coach" "New York" OR "Los Angeles"',
        'site:linkedin.com/in "high ticket coach"',
    ]

    for query in queries:
        try:
            resp = session.get(
                'https://html.duckduckgo.com/html/',
                params={'q': query, 'kl': 'us-en'},
                headers=get_headers('https://duckduckgo.com/'),
                timeout=15
            )
            if resp.status_code != 200:
                continue

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = soup.select('.result__body, .result')

            for result in results[:15]:
                try:
                    link_el = result.select_one('a.result__url, .result__a')
                    snippet_el = result.select_one('.result__snippet')

                    if not link_el:
                        continue

                    link = link_el.get('href', '') or link_el.get_text()
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ''
                    title = link_el.get_text(strip=True)

                    if 'linkedin.com/in/' not in link and 'linkedin.com/in/' not in title:
                        continue

                    linkedin_url = re.search(r'linkedin\.com/in/[a-zA-Z0-9_-]+', link + title)
                    if not linkedin_url:
                        continue

                    combined = f"{title} {snippet}"
                    name = re.sub(r'\s*[-|].*', '', title).strip()[:80]

                    lead = {
                        'name': name,
                        'linkedin_url': 'https://www.' + linkedin_url.group(0),
                        'bio': snippet[:500],
                        'country': detect_country(combined) or 'US',
                        'niche': detect_niche(combined),
                        'source': 'linkedin',
                        'raw_data': {'query': query},
                    }
                    passes, score = qualify_lead(lead)
                    lead['qualification_score'] = score
                    lead['is_high_ticket'] = score >= 6
                    lead['has_website'] = True

                    if passes or is_coaching_profile(combined):
                        leads.append(lead)

                except Exception:
                    pass

            random_delay(3, 5)

        except Exception as e:
            logger.error(f"DuckDuckGo LinkedIn search error: {e}")

    return leads


def _parse_linkedin_html(html: str, search_term: str, country: str) -> List[dict]:
    from bs4 import BeautifulSoup
    leads = []

    soup = BeautifulSoup(html, 'html.parser')

    # Try structured data
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get('@type') == 'Person':
                lead = _ld_json_to_lead(data, country, search_term)
                if lead:
                    leads.append(lead)
        except Exception:
            pass

    # Parse profile cards
    selectors = [
        '.search-result__wrapper',
        '.reusable-search__result-container',
        '.entity-result',
        '.org-people-profile-card',
        '.search-result',
    ]
    cards = []
    for sel in selectors:
        cards = soup.select(sel)
        if cards:
            break

    for card in cards[:20]:
        try:
            name_el = card.select_one('span[aria-hidden="true"], .actor-name, .entity-result__title-text a span')
            name = name_el.get_text(strip=True) if name_el else None
            if not name:
                continue

            headline_el = card.select_one('.entity-result__primary-subtitle, .subline-level-1, .actor-mini-card__occupation')
            headline = headline_el.get_text(strip=True) if headline_el else ''

            location_el = card.select_one('.entity-result__secondary-subtitle, .subline-level-2')
            location = location_el.get_text(strip=True) if location_el else ''

            link_el = card.select_one('a[href*="/in/"]')
            linkedin_url = None
            if link_el:
                href = link_el.get('href', '')
                match = re.search(r'/in/[a-zA-Z0-9_-]+', href)
                if match:
                    linkedin_url = 'https://www.linkedin.com' + match.group(0)

            combined = f"{name} {headline} {location} {search_term}"
            lead = {
                'name': name[:80],
                'linkedin_url': linkedin_url,
                'location': location[:100] if location else None,
                'country': detect_country(combined) or country,
                'niche': detect_niche(combined),
                'bio': headline[:500] if headline else None,
                'source': 'linkedin',
                'raw_data': {'search_term': search_term},
            }
            passes, score = qualify_lead(lead)
            lead['qualification_score'] = score
            lead['is_high_ticket'] = score >= 6
            lead['has_website'] = bool(linkedin_url)

            if passes or is_coaching_profile(combined):
                leads.append(lead)

        except Exception:
            pass

    return leads


def _ld_json_to_lead(data: dict, country: str, search_term: str) -> dict:
    name = data.get('name')
    if not name:
        return None

    combined = f"{name} {data.get('description', '')} {data.get('jobTitle', '')} {search_term}"
    lead = {
        'name': name[:80],
        'email': data.get('email'),
        'website': data.get('url') or data.get('sameAs', [None])[0] if isinstance(data.get('sameAs'), list) else data.get('sameAs'),
        'location': data.get('address', {}).get('addressLocality') if isinstance(data.get('address'), dict) else None,
        'country': detect_country(str(data.get('address', '')) + country) or country,
        'niche': detect_niche(combined),
        'bio': data.get('description', '')[:500],
        'source': 'linkedin',
        'raw_data': {'search_term': search_term},
    }
    passes, score = qualify_lead(lead)
    lead['qualification_score'] = score
    lead['is_high_ticket'] = score >= 6
    lead['has_website'] = bool(lead.get('website'))
    return lead if passes else None

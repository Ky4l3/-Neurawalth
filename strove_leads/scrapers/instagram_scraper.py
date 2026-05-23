import requests
import logging
import json
import re
from typing import List
from .base_scraper import (
    get_headers, random_delay, detect_country, detect_niche,
    qualify_lead, extract_website_from_text, is_coaching_profile,
    is_high_ticket
)

logger = logging.getLogger(__name__)

HASHTAGS = [
    'businesscoach',
    'lifecoach',
    'executivecoach',
    'highticketcoach',
    'onlinecoach',
    'mindsetcoach',
    'certifiedcoach',
    'transformationcoach',
    'businessmentor',
    'entrepreneurcoach',
    'womenentrepreneur',
    'successcoach',
    'leadershipcoach',
    'marketingcoach',
    'salescoach',
]


def scrape_instagram_source() -> List[dict]:
    leads = []

    # Try Playwright approach first (more reliable)
    try:
        from playwright.sync_api import sync_playwright
        leads = _scrape_instagram_playwright()
    except ImportError:
        logger.warning("Playwright not available, using requests-based Instagram scraping")
        leads = _scrape_instagram_requests()
    except Exception as e:
        logger.error(f"Playwright Instagram error: {e}")
        leads = _scrape_instagram_requests()

    return leads


def _scrape_instagram_playwright() -> List[dict]:
    from playwright.sync_api import sync_playwright
    leads = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--no-zygote']
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 900},
            locale='en-US',
        )
        page = context.new_page()

        for tag in HASHTAGS[:8]:
            try:
                url = f'https://www.instagram.com/explore/tags/{tag}/'
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
                random_delay(3, 5)

                # Check for login wall
                content = page.content()
                if 'Log in' in content and 'login' in page.url:
                    logger.info(f"Instagram requires login for #{tag}, skipping")
                    continue

                # Extract from page JSON data
                json_data = _extract_instagram_json(content)
                if json_data:
                    tag_leads = _parse_instagram_hashtag_data(json_data, tag)
                    leads.extend(tag_leads)
                    logger.info(f"Instagram #{tag}: found {len(tag_leads)} profiles")

                random_delay(5, 10)

            except Exception as e:
                logger.error(f"Instagram Playwright error for #{tag}: {e}")

        browser.close()

    return leads


def _scrape_instagram_requests() -> List[dict]:
    """Requests-based fallback for Instagram hashtag pages."""
    leads = []
    session = requests.Session()

    for tag in HASHTAGS[:6]:
        try:
            url = f'https://www.instagram.com/explore/tags/{tag}/'
            resp = session.get(url, headers=get_headers('https://www.instagram.com/'), timeout=15)

            if resp.status_code != 200:
                logger.warning(f"Instagram returned {resp.status_code} for #{tag}")
                random_delay(5, 10)
                continue

            json_data = _extract_instagram_json(resp.text)
            if json_data:
                tag_leads = _parse_instagram_hashtag_data(json_data, tag)
                leads.extend(tag_leads)

            random_delay(8, 15)

        except Exception as e:
            logger.error(f"Instagram requests error for #{tag}: {e}")

    # Supplement with Google search for Instagram profiles
    google_leads = _google_instagram_search(session)
    leads.extend(google_leads)

    return leads


def _extract_instagram_json(html: str) -> dict:
    """Extract embedded JSON from Instagram page."""
    # Try window._sharedData
    match = re.search(r'window\._sharedData\s*=\s*({.+?});</script>', html)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Try __additionalDataLoaded
    match = re.search(r'__additionalDataLoaded\([^,]+,\s*({.+?})\)', html)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Try script tags with application/json
    for match in re.finditer(r'<script type="application/json"[^>]*>({.+?})</script>', html, re.DOTALL):
        try:
            data = json.loads(match.group(1))
            if 'hashtag' in str(data) or 'edge_hashtag' in str(data):
                return data
        except Exception:
            pass

    return None


def _parse_instagram_hashtag_data(data: dict, tag: str) -> List[dict]:
    """Parse Instagram hashtag JSON data to extract profiles."""
    leads = []
    profiles_seen = set()

    # Navigate the nested structure
    def find_edges(obj, depth=0):
        if depth > 10 or not isinstance(obj, dict):
            return []
        found = []
        for key, val in obj.items():
            if key == 'edges' and isinstance(val, list):
                found.extend(val)
            elif isinstance(val, (dict, list)):
                if isinstance(val, dict):
                    found.extend(find_edges(val, depth + 1))
                elif isinstance(val, list):
                    for item in val:
                        found.extend(find_edges(item, depth + 1))
        return found

    edges = find_edges(data)

    for edge in edges:
        try:
            node = edge.get('node', edge)
            if not isinstance(node, dict):
                continue

            owner = node.get('owner', {})
            if not owner:
                continue

            username = owner.get('username') or node.get('username')
            if not username or username in profiles_seen:
                continue
            profiles_seen.add(username)

            full_name = owner.get('full_name', '') or ''
            bio = owner.get('biography', '') or node.get('accessibility_caption', '') or ''
            follower_count = owner.get('edge_followed_by', {}).get('count', 0)
            website = owner.get('external_url') or extract_website_from_text(bio)
            profile_pic = owner.get('profile_pic_url', '')

            combined = f"{full_name} {bio} {username}"
            country = detect_country(combined)
            niche = detect_niche(combined + ' ' + tag)

            if follower_count and not (1000 <= follower_count <= 500000):
                continue

            lead = {
                'name': full_name or username,
                'instagram_handle': username,
                'website': website,
                'bio': bio[:500] if bio else None,
                'follower_count': follower_count or None,
                'country': country,
                'niche': niche,
                'source': 'instagram',
                'raw_data': {'tag': tag, 'username': username},
            }

            passes, score = qualify_lead(lead)
            lead['qualification_score'] = score
            lead['is_high_ticket'] = is_high_ticket(bio)
            lead['has_website'] = bool(website)

            if passes or (is_coaching_profile(combined) and website):
                leads.append(lead)

        except Exception:
            pass

    return leads


def _google_instagram_search(session: requests.Session) -> List[dict]:
    """Use DuckDuckGo to find Instagram coaching profiles."""
    leads = []
    queries = [
        'site:instagram.com "business coach" "link in bio" "apply"',
        'site:instagram.com "high ticket coach" "program" "results"',
        'site:instagram.com "life coach" "transformation" "apply now"',
        'site:instagram.com "executive coach" "corporate" "leader"',
        'site:instagram.com "mindset coach" "program" "VIP"',
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

            for result in results[:12]:
                try:
                    link_el = result.select_one('a.result__url, .result__a, a')
                    snippet_el = result.select_one('.result__snippet')

                    if not link_el:
                        continue

                    href = link_el.get('href', '')
                    title = link_el.get_text(strip=True)
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ''

                    ig_match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)', href + title)
                    if not ig_match:
                        continue

                    handle = ig_match.group(1)
                    if handle in ('p', 'explore', 'reel', 'stories', 'tv', 'tags'):
                        continue

                    combined = f"{title} {snippet}"
                    bio = snippet[:500]
                    website = extract_website_from_text(snippet)
                    country = detect_country(combined)
                    niche = detect_niche(combined + ' ' + query)
                    name = title.split('(')[0].split('@')[0].strip()
                    name = re.sub(r'\s*[|\-].*', '', name).strip()[:80]

                    lead = {
                        'name': name or handle,
                        'instagram_handle': handle,
                        'website': website,
                        'bio': bio,
                        'country': country,
                        'niche': niche,
                        'source': 'instagram',
                        'raw_data': {'query': query, 'handle': handle},
                    }
                    passes, score = qualify_lead(lead)
                    lead['qualification_score'] = score
                    lead['is_high_ticket'] = is_high_ticket(bio)
                    lead['has_website'] = bool(website)

                    if passes or is_coaching_profile(combined):
                        leads.append(lead)

                except Exception:
                    pass

            random_delay(2, 4)

        except Exception as e:
            logger.error(f"DuckDuckGo Instagram search error: {e}")

    return leads

import requests
import logging
import json
import os
import re
from typing import List
from .base_scraper import (
    get_headers, random_delay, detect_country, detect_niche,
    qualify_lead, extract_email_from_text, extract_website_from_text
)

logger = logging.getLogger(__name__)

SEARCH_QUERIES = [
    '"business coach" site:instagram.com',
    '"life coach" site:instagram.com',
    '"executive coach" site:instagram.com',
    '"high ticket coach" site:instagram.com',
    '"mindset coach" site:instagram.com',
    '"transformation coach" site:instagram.com',
    '"online mentor" site:instagram.com',
    '"certified business coach" site:instagram.com',
    '"business coach" site:linkedin.com',
    '"executive coach" site:linkedin.com',
]


def scrape_google_source(queries: List[str] = None, serp_api_key: str = None, pages: int = 3) -> List[dict]:
    """Scrape Google search results for coaching profiles."""
    if queries is None:
        queries = SEARCH_QUERIES

    leads = []
    errors = []

    for query in queries:
        try:
            if serp_api_key:
                results = _scrape_with_serpapi(query, serp_api_key, pages)
            else:
                results = _scrape_with_duckduckgo(query, pages)

            for result in results:
                lead = _parse_search_result(result, query)
                if lead:
                    leads.append(lead)

            random_delay(3, 6)
        except Exception as e:
            logger.error(f"Google scrape error for query '{query}': {e}")
            errors.append(str(e))

    logger.info(f"Google scraper found {len(leads)} raw leads")
    return leads


def _scrape_with_serpapi(query: str, api_key: str, pages: int = 3) -> List[dict]:
    results = []
    for page in range(pages):
        try:
            resp = requests.get(
                'https://serpapi.com/search',
                params={
                    'q': query,
                    'api_key': api_key,
                    'num': 10,
                    'start': page * 10,
                    'gl': 'us',
                    'hl': 'en',
                },
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                organic = data.get('organic_results', [])
                results.extend(organic)
            random_delay(1, 2)
        except Exception as e:
            logger.error(f"SerpAPI error: {e}")
    return results


def _scrape_with_duckduckgo(query: str, pages: int = 3) -> List[dict]:
    """Fallback: use DuckDuckGo HTML search."""
    results = []
    session = requests.Session()

    try:
        # Get VQD token
        resp = session.get(
            'https://duckduckgo.com/',
            headers=get_headers(),
            timeout=10
        )
        vqd_match = re.search(r'vqd=([\d-]+)', resp.text)
        if not vqd_match:
            return []
        vqd = vqd_match.group(1)

        for page in range(pages):
            resp = session.get(
                'https://links.duckduckgo.com/d.js',
                params={
                    'q': query,
                    'vqd': vqd,
                    's': str(page * 30),
                    'dl': 'en',
                    'ct': 'US',
                    'ss_mkt': 'us',
                    'df': '',
                    'ex': '-1',
                    'sp': '1',
                },
                headers=get_headers('https://duckduckgo.com/'),
                timeout=10
            )
            if resp.status_code != 200:
                break

            # Parse JSON results
            try:
                text = resp.text
                json_start = text.find('[')
                json_end = text.rfind(']') + 1
                if json_start > -1 and json_end > json_start:
                    items = json.loads(text[json_start:json_end])
                    for item in items:
                        if isinstance(item, dict) and item.get('u'):
                            results.append({
                                'link': item.get('u', ''),
                                'title': item.get('t', ''),
                                'snippet': item.get('a', ''),
                            })
            except Exception:
                pass

            random_delay(2, 4)

    except Exception as e:
        logger.error(f"DuckDuckGo scrape error: {e}")

    return results


def _parse_search_result(result: dict, query: str) -> dict:
    link = result.get('link', '')
    title = result.get('title', '')
    snippet = result.get('snippet', '') or result.get('a', '')

    if not link:
        return None

    combined = f"{title} {snippet}"
    source_sub = 'google_instagram' if 'instagram.com' in link else 'google_linkedin'
    instagram_handle = None
    linkedin_url = None

    if 'instagram.com' in link:
        match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)', link)
        if match:
            handle = match.group(1)
            if handle not in ('p', 'explore', 'reel', 'stories', 'tv'):
                instagram_handle = handle
            else:
                return None
    elif 'linkedin.com' in link:
        if '/in/' in link or '/company/' in link:
            linkedin_url = link.split('?')[0]
        else:
            return None

    name = title.split('(')[0].split('@')[0].strip()
    name = re.sub(r'\s*\|\s*.*', '', name).strip()
    if len(name) > 60:
        name = name[:60]

    location = None
    country = detect_country(combined)
    niche = detect_niche(combined + ' ' + query)
    website = extract_website_from_text(snippet)
    email = extract_email_from_text(snippet)

    lead = {
        'name': name or 'Unknown',
        'email': email,
        'website': website,
        'instagram_handle': instagram_handle,
        'linkedin_url': linkedin_url,
        'location': location,
        'country': country,
        'niche': niche,
        'bio': snippet[:500] if snippet else None,
        'source': source_sub,
        'raw_data': {'query': query, 'link': link, 'title': title},
    }

    passes, score = qualify_lead(lead)
    lead['qualification_score'] = score
    lead['is_high_ticket'] = score >= 6
    lead['has_website'] = bool(website or linkedin_url)

    if not passes and not (instagram_handle or linkedin_url):
        return None

    return lead

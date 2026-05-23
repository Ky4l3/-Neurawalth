import requests
from bs4 import BeautifulSoup
import logging
import re
import json
from typing import List
from .base_scraper import (
    get_headers, random_delay, detect_country, detect_niche,
    qualify_lead, extract_email_from_text, extract_website_from_text,
    is_coaching_profile
)

logger = logging.getLogger(__name__)


def scrape_directories_source() -> List[dict]:
    leads = []
    scrapers = [
        ('noomii', _scrape_noomii),
        ('coachme', _scrape_coachme),
        ('thecoachingdirectory', _scrape_coaching_directory),
        ('bark', _scrape_bark),
    ]
    for name, fn in scrapers:
        try:
            results = fn()
            leads.extend(results)
            logger.info(f"Directory '{name}' found {len(results)} leads")
            random_delay(3, 6)
        except Exception as e:
            logger.error(f"Directory scraper '{name}' failed: {e}")
    return leads


def _scrape_noomii() -> List[dict]:
    leads = []
    base_url = 'https://www.noomii.com/life-coaches'
    urls = [
        'https://www.noomii.com/life-coaches',
        'https://www.noomii.com/business-coaches',
        'https://www.noomii.com/executive-coaches',
        'https://www.noomii.com/career-coaches',
        'https://www.noomii.com/health-coaches',
    ]

    session = requests.Session()
    for url in urls:
        try:
            for page in range(1, 5):
                page_url = f"{url}?page={page}"
                resp = session.get(page_url, headers=get_headers(base_url), timeout=15)
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, 'html.parser')
                coach_cards = soup.select('.coach-card, .coach-listing, article.coach, .profile-card')

                if not coach_cards:
                    # Try generic approach
                    coach_cards = soup.select('[class*="coach"]')[:20]

                for card in coach_cards:
                    try:
                        lead = _parse_noomii_card(card, url)
                        if lead:
                            leads.append(lead)
                    except Exception:
                        pass

                random_delay(2, 4)

                # If fewer than 5 coaches found on page, assume no more pages
                if len(coach_cards) < 5:
                    break

        except Exception as e:
            logger.error(f"Noomii error for {url}: {e}")

    return leads


def _parse_noomii_card(card, source_url: str) -> dict:
    name_el = card.select_one('h2, h3, .coach-name, [class*="name"]')
    name = name_el.get_text(strip=True) if name_el else None
    if not name or len(name) < 2:
        return None

    link_el = card.select_one('a[href*="/coaches/"]')
    profile_url = None
    if link_el:
        href = link_el.get('href', '')
        if href.startswith('http'):
            profile_url = href
        else:
            profile_url = 'https://www.noomii.com' + href

    bio_el = card.select_one('.bio, .description, p, [class*="bio"]')
    bio = bio_el.get_text(strip=True)[:500] if bio_el else None

    location_el = card.select_one('.location, [class*="location"], [class*="city"]')
    location = location_el.get_text(strip=True) if location_el else None

    combined = f"{name} {bio or ''} {location or ''}"
    country = detect_country(combined)
    niche = detect_niche(combined)

    email = extract_email_from_text(card.get_text())
    website = extract_website_from_text(card.get_text())

    lead = {
        'name': name,
        'email': email,
        'website': website or profile_url,
        'location': location,
        'country': country,
        'niche': niche,
        'bio': bio,
        'source': 'noomii',
        'raw_data': {'profile_url': profile_url, 'source_url': source_url},
    }

    passes, score = qualify_lead(lead)
    lead['qualification_score'] = score
    lead['is_high_ticket'] = score >= 6
    lead['has_website'] = bool(website or profile_url)

    if not passes and not is_coaching_profile(combined):
        return None

    return lead


def _scrape_coachme() -> List[dict]:
    leads = []
    urls = [
        'https://www.coach.me/coaches?categoryId=10',  # Business
        'https://www.coach.me/coaches?categoryId=14',  # Life
        'https://www.coach.me/coaches?categoryId=24',  # Executive
    ]
    session = requests.Session()

    for url in urls:
        try:
            for page in range(1, 4):
                page_url = f"{url}&page={page}"
                resp = session.get(page_url, headers=get_headers('https://www.coach.me/'), timeout=15)
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, 'html.parser')
                cards = soup.select('.coach-card, .coach, article[class*="coach"], .profile')

                if not cards:
                    scripts = soup.find_all('script', type='application/json')
                    for script in scripts:
                        try:
                            data = json.loads(script.string)
                            coaches = _extract_coaches_from_json(data)
                            leads.extend(coaches)
                        except Exception:
                            pass
                    break

                for card in cards:
                    try:
                        lead = _parse_coach_card_generic(card, 'coachme')
                        if lead:
                            leads.append(lead)
                    except Exception:
                        pass

                random_delay(2, 4)

        except Exception as e:
            logger.error(f"Coach.me error for {url}: {e}")

    return leads


def _extract_coaches_from_json(data, source: str = 'coachme') -> List[dict]:
    leads = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and ('name' in item or 'coach' in str(item.keys()).lower()):
                lead = _coach_dict_to_lead(item, source)
                if lead:
                    leads.append(lead)
    elif isinstance(data, dict):
        for key in ('coaches', 'results', 'data', 'items'):
            if key in data and isinstance(data[key], list):
                for item in data[key]:
                    lead = _coach_dict_to_lead(item, source)
                    if lead:
                        leads.append(lead)
    return leads


def _coach_dict_to_lead(item: dict, source: str) -> dict:
    name = item.get('name') or item.get('full_name') or item.get('displayName')
    if not name:
        return None

    bio = item.get('bio') or item.get('description') or item.get('about', '')
    location = item.get('location') or item.get('city', '')
    website = item.get('website') or item.get('url') or item.get('profile_url')
    email = item.get('email') or extract_email_from_text(str(bio))
    combined = f"{name} {bio} {location}"

    lead = {
        'name': str(name)[:100],
        'email': email,
        'website': str(website)[:200] if website else None,
        'location': str(location)[:100] if location else None,
        'country': detect_country(combined),
        'niche': detect_niche(combined),
        'bio': str(bio)[:500] if bio else None,
        'source': source,
        'raw_data': item,
    }
    passes, score = qualify_lead(lead)
    lead['qualification_score'] = score
    lead['is_high_ticket'] = score >= 6
    lead['has_website'] = bool(website)
    return lead if (passes or is_coaching_profile(combined)) else None


def _parse_coach_card_generic(card, source: str) -> dict:
    name_el = card.select_one('h2, h3, h4, .name, [class*="name"]')
    name = name_el.get_text(strip=True) if name_el else None
    if not name:
        return None

    bio_el = card.select_one('.bio, .description, .about, p')
    bio = bio_el.get_text(strip=True)[:500] if bio_el else None

    location_el = card.select_one('.location, .city, [class*="location"]')
    location = location_el.get_text(strip=True) if location_el else None

    link_el = card.select_one('a')
    href = link_el.get('href', '') if link_el else ''
    website = href if href.startswith('http') else None

    email = extract_email_from_text(card.get_text())
    combined = f"{name} {bio or ''} {location or ''}"

    lead = {
        'name': name[:100],
        'email': email,
        'website': website,
        'location': location,
        'country': detect_country(combined),
        'niche': detect_niche(combined),
        'bio': bio,
        'source': source,
        'raw_data': {'text_preview': card.get_text()[:200]},
    }
    passes, score = qualify_lead(lead)
    lead['qualification_score'] = score
    lead['is_high_ticket'] = score >= 6
    lead['has_website'] = bool(website)
    return lead if passes else None


def _scrape_coaching_directory() -> List[dict]:
    leads = []
    urls = [
        'https://thecoachingdirectory.com/coaches/business-coaching',
        'https://thecoachingdirectory.com/coaches/life-coaching',
        'https://thecoachingdirectory.com/coaches/executive-coaching',
    ]
    session = requests.Session()

    for url in urls:
        try:
            for page in range(1, 5):
                page_url = f"{url}?page={page}"
                resp = session.get(page_url, headers=get_headers('https://thecoachingdirectory.com/'), timeout=15)
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, 'html.parser')
                cards = soup.select('.coach-profile, .listing, article, .coach-card, [class*="coach"]')

                if not cards:
                    break

                for card in cards[:30]:
                    try:
                        lead = _parse_coach_card_generic(card, 'thecoachingdirectory')
                        if lead:
                            leads.append(lead)
                    except Exception:
                        pass

                random_delay(2, 4)
                if len(cards) < 5:
                    break

        except Exception as e:
            logger.error(f"TheCoachingDirectory error for {url}: {e}")

    return leads


def _scrape_bark() -> List[dict]:
    leads = []
    urls = [
        'https://www.bark.com/en/us/life-coaches/',
        'https://www.bark.com/en/gb/life-coaches/',
        'https://www.bark.com/en/us/business-coaches/',
        'https://www.bark.com/en/gb/business-coaches/',
    ]
    session = requests.Session()

    for url in urls:
        try:
            resp = session.get(url, headers=get_headers('https://www.bark.com/'), timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')
            cards = soup.select('.provider-card, .expert-card, .listing-card, [class*="provider"]')

            for card in cards[:40]:
                try:
                    lead = _parse_coach_card_generic(card, 'bark')
                    if lead:
                        # Infer country from URL
                        if '/en/us/' in url:
                            lead['country'] = lead['country'] or 'US'
                        elif '/en/gb/' in url:
                            lead['country'] = lead['country'] or 'UK'
                        leads.append(lead)
                except Exception:
                    pass

            random_delay(2, 4)

        except Exception as e:
            logger.error(f"Bark error for {url}: {e}")

    return leads

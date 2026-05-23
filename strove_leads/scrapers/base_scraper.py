import random
import time
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
]

HIGH_TICKET_KEYWORDS = [
    'high ticket', 'highticket', 'high-ticket', 'vip', 'premium',
    'apply now', 'apply here', 'application', 'private coaching',
    'mastermind', 'exclusive', '10k', '5k', '2k', '$10,000', '$5,000',
    'program', 'intensive', 'retreat', '1:1', 'one-on-one',
    'results guaranteed', 'transformation', 'invest in yourself',
]

COACHING_KEYWORDS = [
    'coach', 'coaching', 'mentor', 'mentoring', 'consultant',
    'consulting', 'advisor', 'trainer', 'facilitator',
    'business coach', 'life coach', 'executive coach', 'mindset coach',
    'success coach', 'performance coach', 'leadership coach',
]

SKIP_KEYWORDS = [
    'marketing agency', 'full marketing team', 'social media agency',
    'digital agency', 'we offer marketing', 'our agency',
    'seo agency', 'ppc agency',
]

COUNTRY_MAP = {
    'united states': 'US', 'usa': 'US', 'u.s.': 'US', 'u.s.a': 'US',
    'united kingdom': 'UK', 'uk': 'UK', 'england': 'UK', 'scotland': 'UK',
    'wales': 'UK', 'great britain': 'UK',
    'canada': 'CA', 'australia': 'AU',
    'new york': 'US', 'los angeles': 'US', 'chicago': 'US', 'houston': 'US',
    'london': 'UK', 'manchester': 'UK', 'birmingham': 'UK',
    'toronto': 'CA', 'vancouver': 'CA', 'montreal': 'CA',
    'sydney': 'AU', 'melbourne': 'AU', 'brisbane': 'AU',
}

NICHE_MAP = {
    'business coach': 'Business Coach',
    'life coach': 'Life Coach',
    'executive coach': 'Executive Coach',
    'mindset coach': 'Mindset Coach',
    'health coach': 'Health Coach',
    'fitness coach': 'Fitness Coach',
    'relationship coach': 'Relationship Coach',
    'leadership coach': 'Leadership Coach',
    'career coach': 'Career Coach',
    'sales coach': 'Sales Coach',
    'transformation coach': 'Transformation Coach',
    'performance coach': 'Performance Coach',
    'spiritual coach': 'Spiritual Coach',
    'marketing coach': 'Marketing Coach',
    'financial coach': 'Financial Coach',
}


def random_delay(min_s: float = 2.0, max_s: float = 5.0):
    time.sleep(random.uniform(min_s, max_s))


def get_random_ua() -> str:
    return random.choice(USER_AGENTS)


def get_headers(referer: str = None) -> dict:
    headers = {
        'User-Agent': get_random_ua(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
    if referer:
        headers['Referer'] = referer
    return headers


def detect_country(text: str) -> Optional[str]:
    if not text:
        return None
    text_lower = text.lower()
    for keyword, country in COUNTRY_MAP.items():
        if keyword in text_lower:
            return country
    return None


def detect_niche(text: str) -> str:
    if not text:
        return 'Coach'
    text_lower = text.lower()
    for keyword, niche in NICHE_MAP.items():
        if keyword in text_lower:
            return niche
    if 'coach' in text_lower:
        return 'Coach'
    if 'mentor' in text_lower:
        return 'Mentor'
    if 'consultant' in text_lower:
        return 'Consultant'
    return 'Coach'


def is_high_ticket(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in HIGH_TICKET_KEYWORDS)


def is_coaching_profile(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in COACHING_KEYWORDS)


def should_skip(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in SKIP_KEYWORDS)


def qualify_lead(lead: dict) -> tuple[bool, int]:
    """Score and qualify a lead. Returns (passes_threshold, score)."""
    score = 0
    combined_text = ' '.join(filter(None, [
        lead.get('bio', ''),
        lead.get('name', ''),
        lead.get('niche', ''),
        lead.get('location', ''),
    ]))

    if should_skip(combined_text):
        return False, 0

    if is_coaching_profile(combined_text):
        score += 2

    if lead.get('website') or lead.get('linkedin_url'):
        score += 2

    if lead.get('country') in ('US', 'UK', 'CA', 'AU'):
        score += 2

    if is_high_ticket(combined_text):
        score += 2

    follower_count = lead.get('follower_count', 0) or 0
    if 1000 <= follower_count <= 500000:
        score += 1

    # Require at least some contact info
    has_contact = any([lead.get('email'), lead.get('website'), lead.get('instagram_handle'), lead.get('linkedin_url')])
    if not has_contact:
        return False, score

    # Must have at least bio mentioning coaching + one of the other signals
    return score >= 3, score


def extract_email_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(pattern, text)
    for m in matches:
        if not any(skip in m.lower() for skip in ['example.com', 'test.com', 'email.com']):
            return m
    return None


def extract_website_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    pattern = r'https?://[^\s<>"\'{}|\\^`\[\]]+'
    matches = re.findall(pattern, text)
    for m in matches:
        if not any(skip in m for skip in ['instagram.com', 'facebook.com', 'twitter.com', 'linkedin.com']):
            return m
    # Try linktr.ee or bio links
    linktree = re.search(r'linktr\.ee/[^\s]+', text)
    if linktree:
        return 'https://' + linktree.group(0)
    return None

import requests
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def find_email_hunter(name: str, domain: str, api_key: str) -> Optional[str]:
    """Find email using Hunter.io API."""
    if not api_key or not domain:
        return None
    try:
        parts = name.split() if name else ['']
        params = {
            'domain': domain.replace('https://', '').replace('http://', '').split('/')[0],
            'api_key': api_key,
        }
        if len(parts) >= 2:
            params['first_name'] = parts[0]
            params['last_name'] = parts[-1]

        resp = requests.get(
            'https://api.hunter.io/v2/email-finder',
            params=params,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get('data', {}).get('email')
    except Exception as e:
        logger.error(f"Hunter.io error: {e}")
    return None


def find_email_snov(name: str, domain: str, access_token: str) -> Optional[str]:
    """Find email using Snov.io API."""
    if not access_token or not domain:
        return None
    try:
        clean_domain = domain.replace('https://', '').replace('http://', '').split('/')[0]
        parts = name.split() if name else ['']
        data = {
            'domain': clean_domain,
            'firstName': parts[0] if parts else '',
            'lastName': parts[-1] if len(parts) > 1 else '',
        }
        resp = requests.post(
            'https://api.snov.io/v1/get-emails-from-names',
            json=data,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
        )
        if resp.status_code == 200:
            result = resp.json()
            emails = result.get('emails', [])
            if emails:
                return emails[0].get('email')
    except Exception as e:
        logger.error(f"Snov.io error: {e}")
    return None


def get_snov_token(client_id: str, client_secret: str) -> Optional[str]:
    """Get Snov.io access token."""
    try:
        resp = requests.post(
            'https://api.snov.io/v1/oauth/access_token',
            json={'grant_type': 'client_credentials', 'client_id': client_id, 'client_secret': client_secret},
            timeout=10
        )
        if resp.status_code == 200:
            return resp.json().get('access_token')
    except Exception as e:
        logger.error(f"Snov.io token error: {e}")
    return None


def enrich_lead_email(lead: dict, hunter_key: str = None, snov_key: str = None) -> dict:
    """Try to find email for a lead if not already present."""
    if lead.get('email'):
        return lead

    name = lead.get('name', '')
    website = lead.get('website', '')

    if not website:
        return lead

    domain = website.replace('https://', '').replace('http://', '').split('/')[0]
    if not domain or '.' not in domain:
        return lead

    email = None
    if hunter_key:
        email = find_email_hunter(name, domain, hunter_key)

    if not email and snov_key:
        email = find_email_snov(name, domain, snov_key)

    if email:
        lead['email'] = email

    return lead

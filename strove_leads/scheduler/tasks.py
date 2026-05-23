import logging
import json
import threading
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database.db import (
    upsert_lead, start_scrape_log, finish_scrape_log,
    get_setting
)

logger = logging.getLogger(__name__)

_scheduler = None
_next_run_time = None


def run_scrape(sources: list = None, state: dict = None):
    """Main scrape runner — runs all sources and saves results."""
    if state is None:
        state = {}

    if sources is None:
        try:
            sources = json.loads(get_setting('enabled_sources', '["google","directories","linkedin","instagram"]'))
        except Exception:
            sources = ['google', 'directories', 'linkedin', 'instagram']

    state['running'] = True
    state['progress'] = 0
    state['message'] = 'Starting scrape...'
    state['last_result'] = None

    log_id = start_scrape_log('all')
    all_leads = []
    errors = []

    serp_api_key = get_setting('serp_api_key', '') or ''
    hunter_api_key = get_setting('hunter_api_key', '') or ''
    snov_api_key = get_setting('snov_api_key', '') or ''

    # Remove masked API keys
    for key in (serp_api_key, hunter_api_key, snov_api_key):
        if '****' in key:
            key = ''

    steps = []
    if 'google' in sources:
        steps.append(('google', _run_google, {'serp_api_key': serp_api_key if '****' not in serp_api_key else ''}))
    if 'directories' in sources:
        steps.append(('directories', _run_directories, {}))
    if 'linkedin' in sources:
        steps.append(('linkedin', _run_linkedin, {'hunter_api_key': hunter_api_key if '****' not in hunter_api_key else ''}))
    if 'instagram' in sources:
        steps.append(('instagram', _run_instagram, {}))

    total_steps = len(steps)

    for i, (name, fn, kwargs) in enumerate(steps):
        try:
            state['message'] = f'Scraping {name}...'
            state['progress'] = int((i / total_steps) * 80)
            logger.info(f"Starting {name} scraper")
            leads = fn(**kwargs)
            all_leads.extend(leads)
            logger.info(f"{name}: found {len(leads)} leads")
        except Exception as e:
            err = f"{name} scraper error: {e}"
            logger.error(err)
            errors.append(err)

    state['message'] = 'Deduplicating and saving leads...'
    state['progress'] = 85

    added_count = 0
    for lead in all_leads:
        try:
            inserted, _ = upsert_lead(lead)
            if inserted:
                added_count += 1
        except Exception as e:
            logger.error(f"Failed to save lead: {e}")

    finish_scrape_log(log_id, len(all_leads), added_count, errors)

    state['running'] = False
    state['progress'] = 100
    state['message'] = f'Complete — {added_count} new leads added ({len(all_leads)} found)'
    state['last_result'] = {
        'leads_found': len(all_leads),
        'leads_added': added_count,
        'errors': len(errors),
        'completed_at': datetime.utcnow().isoformat(),
    }

    logger.info(f"Scrape complete: {added_count}/{len(all_leads)} new leads")


def _run_google(serp_api_key: str = ''):
    from scrapers.google_scraper import scrape_google_source
    try:
        queries = json.loads(get_setting('custom_queries', '[]'))
    except Exception:
        queries = None
    return scrape_google_source(queries=queries or None, serp_api_key=serp_api_key or None)


def _run_directories():
    from scrapers.directory_scraper import scrape_directories_source
    return scrape_directories_source()


def _run_linkedin(hunter_api_key: str = ''):
    from scrapers.linkedin_scraper import scrape_linkedin_source
    return scrape_linkedin_source(hunter_api_key=hunter_api_key or None)


def _run_instagram():
    from scrapers.instagram_scraper import scrape_instagram_source
    return scrape_instagram_source()


def _scheduled_run():
    logger.info("Scheduled scrape starting")
    run_scrape()
    _update_next_run()


def _update_next_run():
    global _next_run_time
    if _scheduler:
        jobs = _scheduler.get_jobs()
        if jobs:
            _next_run_time = jobs[0].next_run_time


def get_next_run_time():
    if _next_run_time:
        return _next_run_time.isoformat()
    return None


def reschedule_job(hour: int, minute: int):
    if _scheduler:
        _scheduler.reschedule_job(
            'daily_scrape',
            trigger=CronTrigger(hour=hour, minute=minute)
        )
        _update_next_run()


def init_scheduler(app):
    global _scheduler

    _scheduler = BackgroundScheduler(daemon=True)

    try:
        hour = int(get_setting('scrape_hour', '6'))
        minute = int(get_setting('scrape_minute', '0'))
    except Exception:
        hour, minute = 6, 0

    _scheduler.add_job(
        _scheduled_run,
        trigger=CronTrigger(hour=hour, minute=minute),
        id='daily_scrape',
        name='Daily Lead Scrape',
        replace_existing=True,
        misfire_grace_time=3600,
    )

    _scheduler.start()
    _update_next_run()
    logger.info(f"Scheduler started — daily scrape at {hour:02d}:{minute:02d} UTC")

    return _scheduler

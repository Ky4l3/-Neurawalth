from flask import Blueprint, request, jsonify
from database.db import get_setting, set_setting, get_db
import json

settings_bp = Blueprint('settings', __name__)

SETTING_KEYS = [
    'scrape_hour', 'scrape_minute', 'serp_api_key', 'hunter_api_key',
    'snov_api_key', 'proxy_list', 'enabled_sources', 'custom_queries',
    'target_countries',
]


@settings_bp.route('/', methods=['GET'])
def get_all_settings():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    result = {row['key']: row['value'] for row in rows}

    # Parse JSON fields
    for key in ('enabled_sources', 'custom_queries', 'target_countries'):
        if key in result:
            try:
                result[key] = json.loads(result[key])
            except Exception:
                pass

    # Mask API keys
    for key in ('serp_api_key', 'hunter_api_key', 'snov_api_key'):
        if result.get(key):
            val = result[key]
            result[key] = val[:4] + '****' + val[-4:] if len(val) > 8 else '****'

    return jsonify(result)


@settings_bp.route('/', methods=['POST'])
def update_settings():
    data = request.json or {}
    updated = []

    for key, value in data.items():
        if key not in SETTING_KEYS:
            continue
        # Serialize lists/dicts
        if isinstance(value, (list, dict)):
            value = json.dumps(value)
        set_setting(key, str(value))
        updated.append(key)

    # Reschedule if time changed
    if 'scrape_hour' in updated or 'scrape_minute' in updated:
        try:
            from scheduler.tasks import reschedule_job
            hour = int(get_setting('scrape_hour', '6'))
            minute = int(get_setting('scrape_minute', '0'))
            reschedule_job(hour, minute)
        except Exception as e:
            pass

    return jsonify({'updated': updated})


@settings_bp.route('/api-key', methods=['POST'])
def save_api_key():
    """Save API key (raw, not masked)."""
    data = request.json or {}
    key_name = data.get('key')
    key_value = data.get('value', '')

    allowed = {'serp_api_key', 'hunter_api_key', 'snov_api_key'}
    if key_name not in allowed:
        return jsonify({'error': 'Invalid key name'}), 400

    set_setting(key_name, key_value)
    return jsonify({'saved': True})

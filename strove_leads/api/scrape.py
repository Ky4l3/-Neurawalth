from flask import Blueprint, jsonify, request, current_app
from database.db import get_scrape_logs, get_db
import threading
import logging

scrape_bp = Blueprint('scrape', __name__)
logger = logging.getLogger(__name__)

_scrape_state = {
    'running': False,
    'progress': 0,
    'message': '',
    'last_result': None,
}


@scrape_bp.route('/status', methods=['GET'])
def scrape_status():
    return jsonify({
        'running': _scrape_state['running'],
        'progress': _scrape_state['progress'],
        'message': _scrape_state['message'],
        'last_result': _scrape_state['last_result'],
    })


@scrape_bp.route('/start', methods=['POST'])
def start_scrape():
    if _scrape_state['running']:
        return jsonify({'error': 'Scrape already running'}), 409

    data = request.json or {}
    sources = data.get('sources', ['google', 'directories', 'linkedin', 'instagram'])

    def run():
        from scheduler.tasks import run_scrape
        run_scrape(sources=sources, state=_scrape_state)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return jsonify({'status': 'started', 'message': 'Scrape started in background'})


@scrape_bp.route('/logs', methods=['GET'])
def scrape_logs():
    limit = int(request.args.get('limit', 20))
    logs = get_scrape_logs(limit)
    return jsonify(logs)

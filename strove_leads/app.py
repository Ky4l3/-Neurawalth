import os
import logging
from flask import Flask, render_template, jsonify
from flask_cors import CORS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'strove-secret-key-change-in-prod')

    db_path = os.environ.get('DB_PATH', 'strove_leads.db')
    os.environ.setdefault('DB_PATH', db_path)

    CORS(app, resources={r'/api/*': {'origins': '*'}})

    from database.db import init_db
    with app.app_context():
        init_db()

    from api.leads import leads_bp
    from api.scrape import scrape_bp
    from api.settings import settings_bp

    app.register_blueprint(leads_bp, url_prefix='/api/leads')
    app.register_blueprint(scrape_bp, url_prefix='/api/scrape')
    app.register_blueprint(settings_bp, url_prefix='/api/settings')

    # Page routes
    @app.route('/')
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/leads')
    def leads():
        return render_template('leads.html')

    @app.route('/export')
    def export_page():
        return render_template('export.html')

    @app.route('/settings')
    def settings():
        return render_template('settings.html')

    @app.route('/health')
    def health():
        return jsonify({'status': 'ok', 'app': 'Strove Leads'})

    return app


app = create_app()

# Start scheduler only in main process (not in Flask reloader child)
if os.environ.get('WERKZEUG_RUN_MAIN') != 'false':
    try:
        from scheduler.tasks import init_scheduler
        init_scheduler(app)
    except Exception as e:
        logger.error(f"Scheduler init failed: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)

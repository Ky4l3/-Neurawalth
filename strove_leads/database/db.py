import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.environ.get('DB_PATH', 'strove_leads.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            website TEXT,
            instagram_handle TEXT,
            linkedin_url TEXT,
            location TEXT,
            country TEXT,
            niche TEXT,
            bio TEXT,
            follower_count INTEGER,
            source TEXT,
            status TEXT DEFAULT 'New',
            qualification_score INTEGER DEFAULT 0,
            is_high_ticket INTEGER DEFAULT 0,
            has_website INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            notes TEXT,
            raw_data TEXT
        );

        CREATE TABLE IF NOT EXISTS scrape_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            completed_at TEXT,
            leads_found INTEGER DEFAULT 0,
            leads_added INTEGER DEFAULT 0,
            errors TEXT,
            source TEXT,
            status TEXT DEFAULT 'running'
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
        CREATE INDEX IF NOT EXISTS idx_leads_instagram ON leads(instagram_handle);
        CREATE INDEX IF NOT EXISTS idx_leads_linkedin ON leads(linkedin_url);
        CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
        CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);
    """)

    # Default settings
    defaults = {
        'scrape_hour': '6',
        'scrape_minute': '0',
        'serp_api_key': '',
        'hunter_api_key': '',
        'snov_api_key': '',
        'proxy_list': '',
        'enabled_sources': json.dumps(['google', 'directories', 'linkedin', 'instagram']),
        'custom_queries': json.dumps([
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
        ]),
        'target_countries': json.dumps(['US', 'UK', 'CA', 'AU']),
    }
    for key, value in defaults.items():
        c.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )

    conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else default


def set_setting(key, value):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, str(value))
    )
    conn.commit()
    conn.close()


def upsert_lead(lead: dict) -> tuple[bool, int]:
    """Insert lead if not duplicate. Returns (inserted, lead_id)."""
    conn = get_db()
    c = conn.cursor()

    # Check for duplicates via email, instagram handle, or linkedin url
    existing_id = None
    if lead.get('email'):
        row = c.execute("SELECT id FROM leads WHERE email=?", (lead['email'],)).fetchone()
        if row:
            existing_id = row['id']

    if not existing_id and lead.get('instagram_handle'):
        row = c.execute("SELECT id FROM leads WHERE instagram_handle=?", (lead['instagram_handle'],)).fetchone()
        if row:
            existing_id = row['id']

    if not existing_id and lead.get('linkedin_url'):
        row = c.execute("SELECT id FROM leads WHERE linkedin_url=?", (lead['linkedin_url'],)).fetchone()
        if row:
            existing_id = row['id']

    if existing_id:
        conn.close()
        return False, existing_id

    c.execute("""
        INSERT INTO leads (
            name, email, phone, website, instagram_handle, linkedin_url,
            location, country, niche, bio, follower_count, source,
            qualification_score, is_high_ticket, has_website, raw_data
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        lead.get('name'), lead.get('email'), lead.get('phone'),
        lead.get('website'), lead.get('instagram_handle'), lead.get('linkedin_url'),
        lead.get('location'), lead.get('country'), lead.get('niche'),
        lead.get('bio'), lead.get('follower_count'), lead.get('source'),
        lead.get('qualification_score', 0), int(lead.get('is_high_ticket', False)),
        int(lead.get('has_website', False)),
        json.dumps(lead.get('raw_data', {}))
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return True, new_id


def get_leads(filters: dict = None, page: int = 1, per_page: int = 50, sort_by: str = 'created_at', sort_dir: str = 'desc'):
    conn = get_db()
    where_clauses = []
    params = []

    if filters:
        if filters.get('status'):
            where_clauses.append("status=?")
            params.append(filters['status'])
        if filters.get('source'):
            where_clauses.append("source=?")
            params.append(filters['source'])
        if filters.get('country'):
            where_clauses.append("country=?")
            params.append(filters['country'])
        if filters.get('niche'):
            where_clauses.append("niche LIKE ?")
            params.append(f"%{filters['niche']}%")
        if filters.get('date_from'):
            where_clauses.append("created_at >= ?")
            params.append(filters['date_from'])
        if filters.get('date_to'):
            where_clauses.append("created_at <= ?")
            params.append(filters['date_to'])
        if filters.get('search'):
            where_clauses.append("(name LIKE ? OR email LIKE ? OR bio LIKE ?)")
            s = f"%{filters['search']}%"
            params.extend([s, s, s])

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    allowed_sort = {'created_at', 'name', 'email', 'status', 'source', 'country', 'niche', 'follower_count', 'qualification_score'}
    sort_col = sort_by if sort_by in allowed_sort else 'created_at'
    direction = 'DESC' if sort_dir.lower() == 'desc' else 'ASC'

    total = conn.execute(f"SELECT COUNT(*) FROM leads {where_sql}", params).fetchone()[0]
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"SELECT * FROM leads {where_sql} ORDER BY {sort_col} {direction} LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


def get_dashboard_stats():
    conn = get_db()
    today = datetime.utcnow().strftime('%Y-%m-%d')

    stats = {
        'total_leads': conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0],
        'leads_today': conn.execute("SELECT COUNT(*) FROM leads WHERE created_at >= ?", (today,)).fetchone()[0],
        'by_source': {},
        'by_status': {},
        'by_country': {},
        'by_niche': {},
        'last_scrape': None,
        'next_scrape': None,
    }

    for row in conn.execute("SELECT source, COUNT(*) as cnt FROM leads GROUP BY source").fetchall():
        stats['by_source'][row['source'] or 'unknown'] = row['cnt']

    for row in conn.execute("SELECT status, COUNT(*) as cnt FROM leads GROUP BY status").fetchall():
        stats['by_status'][row['status']] = row['cnt']

    for row in conn.execute("SELECT country, COUNT(*) as cnt FROM leads WHERE country IS NOT NULL GROUP BY country ORDER BY cnt DESC LIMIT 10").fetchall():
        stats['by_country'][row['country']] = row['cnt']

    for row in conn.execute("SELECT niche, COUNT(*) as cnt FROM leads WHERE niche IS NOT NULL GROUP BY niche ORDER BY cnt DESC LIMIT 10").fetchall():
        stats['by_niche'][row['niche']] = row['cnt']

    last_log = conn.execute(
        "SELECT * FROM scrape_logs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    if last_log:
        stats['last_scrape'] = dict(last_log)

    conn.close()
    return stats


def start_scrape_log(source: str = 'all') -> int:
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO scrape_logs (started_at, source, status) VALUES (?,?,?)",
        (datetime.utcnow().isoformat(), source, 'running')
    )
    log_id = c.lastrowid
    conn.commit()
    conn.close()
    return log_id


def finish_scrape_log(log_id: int, leads_found: int, leads_added: int, errors: list):
    conn = get_db()
    conn.execute("""
        UPDATE scrape_logs SET
            completed_at=?, leads_found=?, leads_added=?, errors=?, status=?
        WHERE id=?
    """, (
        datetime.utcnow().isoformat(),
        leads_found, leads_added,
        json.dumps(errors[:50]),
        'completed',
        log_id
    ))
    conn.commit()
    conn.close()


def get_scrape_logs(limit: int = 20):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM scrape_logs ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

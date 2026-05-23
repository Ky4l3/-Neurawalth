from flask import Blueprint, request, jsonify, Response
from database.db import get_leads, get_db, get_dashboard_stats
import csv
import io
import json

leads_bp = Blueprint('leads', __name__)


@leads_bp.route('/', methods=['GET'])
def list_leads():
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 50)), 200)
    sort_by = request.args.get('sort_by', 'created_at')
    sort_dir = request.args.get('sort_dir', 'desc')

    filters = {
        'status': request.args.get('status'),
        'source': request.args.get('source'),
        'country': request.args.get('country'),
        'niche': request.args.get('niche'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
        'search': request.args.get('search'),
    }
    filters = {k: v for k, v in filters.items() if v}

    leads, total = get_leads(filters, page, per_page, sort_by, sort_dir)

    return jsonify({
        'leads': leads,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
    })


@leads_bp.route('/<int:lead_id>', methods=['GET'])
def get_lead(lead_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Lead not found'}), 404
    return jsonify(dict(row))


@leads_bp.route('/<int:lead_id>', methods=['PATCH'])
def update_lead(lead_id: int):
    data = request.json or {}
    allowed = {'status', 'notes', 'name', 'email', 'phone', 'website', 'niche', 'country'}
    updates = {k: v for k, v in data.items() if k in allowed}

    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400

    conn = get_db()
    row = conn.execute("SELECT id FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Lead not found'}), 404

    set_clause = ', '.join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [lead_id]
    conn.execute(
        f"UPDATE leads SET {set_clause}, updated_at=datetime('now') WHERE id=?",
        values
    )
    conn.commit()

    updated = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    conn.close()
    return jsonify(dict(updated))


@leads_bp.route('/bulk-status', methods=['POST'])
def bulk_update_status():
    data = request.json or {}
    ids = data.get('ids', [])
    status = data.get('status')
    if not ids or not status:
        return jsonify({'error': 'ids and status required'}), 400

    allowed_statuses = {'New', 'Contacted', 'Replied', 'Call Booked', 'Closed', 'Not Qualified'}
    if status not in allowed_statuses:
        return jsonify({'error': 'Invalid status'}), 400

    conn = get_db()
    placeholders = ','.join('?' * len(ids))
    conn.execute(
        f"UPDATE leads SET status=?, updated_at=datetime('now') WHERE id IN ({placeholders})",
        [status] + ids
    )
    conn.commit()
    affected = conn.execute(
        f"SELECT COUNT(*) FROM leads WHERE id IN ({placeholders})", ids
    ).fetchone()[0]
    conn.close()
    return jsonify({'updated': affected})


@leads_bp.route('/export', methods=['GET'])
def export_leads():
    export_format = request.args.get('format', 'csv')
    filters = {
        'status': request.args.get('status'),
        'source': request.args.get('source'),
        'country': request.args.get('country'),
        'niche': request.args.get('niche'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
    }
    filters = {k: v for k, v in filters.items() if v}

    leads, total = get_leads(filters, page=1, per_page=10000)

    if export_format == 'apollo':
        return _export_apollo(leads)
    elif export_format == 'hubspot':
        return _export_hubspot(leads)
    else:
        return _export_standard_csv(leads)


def _export_standard_csv(leads):
    output = io.StringIO()
    fieldnames = [
        'id', 'name', 'email', 'phone', 'website', 'instagram_handle',
        'linkedin_url', 'location', 'country', 'niche', 'bio',
        'follower_count', 'source', 'status', 'qualification_score',
        'is_high_ticket', 'created_at', 'notes'
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for lead in leads:
        writer.writerow(lead)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=strove_leads.csv'}
    )


def _export_apollo(leads):
    output = io.StringIO()
    fieldnames = [
        'First Name', 'Last Name', 'Email', 'Phone', 'Company', 'Website',
        'LinkedIn URL', 'Title', 'City', 'Country', 'Tags', 'Notes'
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for lead in leads:
        name_parts = (lead.get('name') or '').split(' ', 1)
        writer.writerow({
            'First Name': name_parts[0],
            'Last Name': name_parts[1] if len(name_parts) > 1 else '',
            'Email': lead.get('email', ''),
            'Phone': lead.get('phone', ''),
            'Company': '',
            'Website': lead.get('website', ''),
            'LinkedIn URL': lead.get('linkedin_url', ''),
            'Title': lead.get('niche', ''),
            'City': lead.get('location', ''),
            'Country': lead.get('country', ''),
            'Tags': f"Strove,{lead.get('source','')},{lead.get('niche','')}",
            'Notes': lead.get('notes', ''),
        })

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=strove_leads_apollo.csv'}
    )


def _export_hubspot(leads):
    output = io.StringIO()
    fieldnames = [
        'First Name', 'Last Name', 'Email', 'Phone Number', 'Website URL',
        'LinkedIn Bio URL', 'Job Title', 'City', 'Country/Region',
        'Lead Source', 'Notes'
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for lead in leads:
        name_parts = (lead.get('name') or '').split(' ', 1)
        writer.writerow({
            'First Name': name_parts[0],
            'Last Name': name_parts[1] if len(name_parts) > 1 else '',
            'Email': lead.get('email', ''),
            'Phone Number': lead.get('phone', ''),
            'Website URL': lead.get('website', ''),
            'LinkedIn Bio URL': lead.get('linkedin_url', ''),
            'Job Title': lead.get('niche', ''),
            'City': lead.get('location', ''),
            'Country/Region': lead.get('country', ''),
            'Lead Source': f"Strove - {lead.get('source','')}",
            'Notes': lead.get('notes', ''),
        })

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=strove_leads_hubspot.csv'}
    )


@leads_bp.route('/stats', methods=['GET'])
def stats():
    return jsonify(get_dashboard_stats())

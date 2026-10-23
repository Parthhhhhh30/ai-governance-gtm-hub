"""Business rules for the AI Governance GTM Hub. No external dependencies."""
from __future__ import annotations

import csv
import io
import re
import ipaddress
import sqlite3
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / 'data' / 'gtm.db'

FRAMEWORKS = {
    'eu_ai_act': {
        'label': 'EU AI Act', 'type': 'Legislation',
        'question': 'How do you inventory AI use cases, identify relevant actor roles, and determine which controls may apply?',
        'value': 'AI inventory, intake, assessment, and audit evidence',
        'url': 'https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai',
        'caution': 'Do not assume the company is subject to a specific obligation; applicability depends on facts and current dates.'
    },
    'iso42001': {
        'label': 'ISO/IEC 42001', 'type': 'Management-system standard',
        'question': 'How does your team assign ownership, document AI policies, evaluate systems, and improve governance processes?',
        'value': 'documented review workflows, ownership, and governance evidence',
        'url': 'https://www.iso.org/standard/42001',
        'caution': 'A management-system standard is not itself an EU legal mandate; do not imply certification.'
    },
    'nist': {
        'label': 'NIST AI RMF', 'type': 'Voluntary risk framework',
        'question': 'How do you operationalize Govern, Map, Measure, and Manage across AI systems?',
        'value': 'centralized risk records, ownership, and control reviews',
        'url': 'https://airc.nist.gov/airmf-resources/airmf/',
        'caution': 'NIST AI RMF is voluntary; do not present it as a legal requirement.'
    },
}

SIGNALS = {
    'ai_rollout': ('New AI rollout', 24, 'eu_ai_act'),
    'governance_hire': ('AI governance leadership hire', 27, 'iso42001'),
    'regulatory_review': ('AI regulatory programme', 23, 'eu_ai_act'),
    'iso_initiative': ('AI management-system initiative', 19, 'iso42001'),
    'risk_framework': ('AI risk programme', 19, 'nist'),
    'third_party_ai': ('Third-party AI adoption', 15, 'nist'),
    'other': ('Other sourced signal', 7, 'nist'),
}

STAGES = ('New', 'Contacted', 'Replied', 'First meeting booked', 'Not interested')


def connect(db_path: str | Path = DEFAULT_DB):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS accounts (
      id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE,
      industry TEXT DEFAULT '', region TEXT DEFAULT '', website TEXT DEFAULT '', notes TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS contacts (
      id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
      first_name TEXT NOT NULL, last_name TEXT DEFAULT '', title TEXT DEFAULT '',
      email TEXT DEFAULT '', linkedin_url TEXT DEFAULT '', data_source TEXT DEFAULT '',
      verified INTEGER NOT NULL DEFAULT 0, approved INTEGER NOT NULL DEFAULT 0,
      suppressed INTEGER NOT NULL DEFAULT 0, stage TEXT NOT NULL DEFAULT 'New',
      first_meeting_date TEXT DEFAULT '', first_meeting_held INTEGER NOT NULL DEFAULT 0,
      second_meeting_date TEXT DEFAULT '',
      UNIQUE(account_id, email)
    );
    CREATE TABLE IF NOT EXISTS signals (
      id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
      kind TEXT NOT NULL, summary TEXT NOT NULL, source_url TEXT NOT NULL,
      observed_on TEXT NOT NULL, source_reviewed INTEGER NOT NULL DEFAULT 0,
      UNIQUE(account_id, kind, source_url)
    );
    CREATE TABLE IF NOT EXISTS suppression (email TEXT PRIMARY KEY COLLATE NOCASE);
    CREATE INDEX IF NOT EXISTS idx_contacts_account ON contacts(account_id);
    CREATE INDEX IF NOT EXISTS idx_signals_account ON signals(account_id);
    ''')
    conn.commit()


def valid_http_url(value):
    try:
        u = urlparse(value.strip())
        if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password:
            return False
        if any(ch.isspace() or ord(ch) < 32 for ch in value) or '\\' in value:
            return False
        if u.hostname in ('localhost',) or u.hostname.endswith(('.localhost', '.local')):
            return False
        if not re.fullmatch(r'[a-z0-9.-]+', u.hostname, re.IGNORECASE):
            return False
        if '.' not in u.hostname or u.hostname.startswith('.') or u.hostname.endswith('.'):
            return False
        try:
            ip = ipaddress.ip_address(u.hostname)
            if not ip.is_global: return False
        except ValueError:
            pass
        if u.port is not None and u.port not in (80, 443):
            return False
        return True
    except (ValueError, AttributeError):
        return False


def valid_email(value):
    return bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[A-Za-z]{2,}', (value or '').strip()))


def demo_email(value):
    """Prevent reserved, fictional and example identities from outbound CSVs."""
    domain = (value or '').strip().lower().rsplit('@', 1)[-1]
    return (any(domain == suffix or domain.endswith('.' + suffix)
                for suffix in ('example', 'test', 'invalid', 'localhost'))
            or any(domain == root or domain.endswith('.' + root)
                   for root in ('example.com', 'example.org', 'example.net')))


def add_account(conn, name, industry='', region='', website='', notes=''):
    name = name.strip()
    if not name or len(name) > 140:
        raise ValueError('Account name is required (maximum 140 characters).')
    if website and not valid_http_url(website):
        raise ValueError('Website must be an http(s) URL.')
    conn.execute('INSERT OR IGNORE INTO accounts(name, industry, region, website, notes) VALUES (?, ?, ?, ?, ?)',
                 (name, industry.strip(), region.strip(), website.strip(), notes.strip()))
    conn.commit()
    return conn.execute('SELECT id FROM accounts WHERE name = ? COLLATE NOCASE', (name,)).fetchone()['id']


def add_contact(conn, account_id, first_name, last_name='', title='', email='', linkedin_url='', data_source='',
                verified=False, approved=False):
    first_name = first_name.strip()
    email = email.strip().lower()
    if not first_name or len(first_name) > 140:
        raise ValueError('Contact first name is required (maximum 140 characters).')
    if email and not valid_email(email):
        raise ValueError('Invalid work email address.')
    if linkedin_url and not valid_http_url(linkedin_url):
        raise ValueError('LinkedIn URL must be an http(s) URL.')
    suppressed = bool(email and conn.execute('SELECT 1 FROM suppression WHERE email=? COLLATE NOCASE', (email,)).fetchone())
    existing = conn.execute('SELECT id FROM contacts WHERE account_id=? AND email=? COLLATE NOCASE', (account_id, email)).fetchone() if email else None
    if existing:
        return existing['id']
    cursor = conn.execute('''INSERT INTO contacts
       (account_id,first_name,last_name,title,email,linkedin_url,data_source,verified,approved,suppressed)
       VALUES (?,?,?,?,?,?,?,?,?,?)''',
       (account_id, first_name, last_name.strip(), title.strip(), email or None,
        linkedin_url.strip(), data_source.strip(), int(verified), int(approved), int(suppressed)))
    conn.commit()
    return cursor.lastrowid


def add_signal(conn, account_id, kind, summary, source_url, observed_on='', source_reviewed=False):
    if kind not in SIGNALS:
        raise ValueError('Unknown signal type.')
    if not summary.strip() or len(summary) > 600:
        raise ValueError('Please provide a short signal summary (1–600 characters).')
    if not valid_http_url(source_url):
        raise ValueError('A valid source URL is required (no unsupported claims).')
    observed_on = (observed_on or date.today().isoformat()).strip()
    try:
        date.fromisoformat(observed_on)
    except ValueError:
        raise ValueError('Date must be YYYY-MM-DD.')
    if date.fromisoformat(observed_on) > date.today():
        raise ValueError('Signals cannot have dates in the future.')
    conn.execute('''INSERT OR IGNORE INTO signals(account_id,kind,summary,source_url,observed_on,source_reviewed)
        VALUES (?,?,?,?,?,?)''', (account_id, kind, summary.strip(), source_url.strip(), observed_on, int(source_reviewed)))
    conn.commit()


def score_account(signals, today=None):
    """Transparent opportunity priority, NOT an AI-risk or regulatory-compliance rating."""
    today = today or date.today()
    points, reasons, seen = 0, [], set()
    for s in signals:
        if not s['source_reviewed'] or s['kind'] not in SIGNALS or s['kind'] in seen:
            continue
        seen.add(s['kind'])
        observed = date.fromisoformat(s['observed_on'])
        age = max(0, (today - observed).days)
        factor = 1.0 if age <= 90 else 0.6 if age <= 365 else 0.25
        w = round(SIGNALS[s['kind']][1] * factor)
        points += w
        reasons.append(f"{SIGNALS[s['kind']][0]} (+{w})")
    return min(points, 100), reasons


def account_score(conn, account_id):
    ss = conn.execute('SELECT * FROM signals WHERE account_id=? ORDER BY observed_on DESC', (account_id,)).fetchall()
    return score_account(ss)


def qualified(contact):
    """Enzai job-ad meaning: first meeting actually held, second meeting in diary."""
    try:
        return bool(contact['first_meeting_held'] and contact['first_meeting_date'] and contact['second_meeting_date']
                    and date.fromisoformat(contact['first_meeting_date']) <= date.today()
                    and date.fromisoformat(contact['second_meeting_date']) > date.fromisoformat(contact['first_meeting_date']))
    except (ValueError, TypeError):
        return False


def suppress(conn, email):
    email = email.strip().lower()
    if not valid_email(email):
        raise ValueError('Valid email is required for suppression.')
    conn.execute('INSERT OR IGNORE INTO suppression(email) VALUES (?)', (email,))
    conn.execute('UPDATE contacts SET suppressed=1 WHERE lower(email)=?', (email,))
    conn.commit()


def export_eligible(conn, contact):
    if not valid_email(contact['email']) or demo_email(contact['email']):
        return False
    if not contact['verified'] or not contact['approved'] or contact['suppressed']:
        return False
    if contact['stage'] == 'Not interested':
        return False
    return conn.execute('SELECT 1 FROM suppression WHERE email=? COLLATE NOCASE', (contact['email'],)).fetchone() is None


def choose_signal(conn, account_id):
    signals = conn.execute('SELECT * FROM signals WHERE account_id=? AND source_reviewed=1 ORDER BY observed_on DESC',
                           (account_id,)).fetchall()
    return signals[0] if signals else None


def make_draft(conn, contact_id):
    contact = conn.execute('''SELECT c.*, a.name AS company FROM contacts c JOIN accounts a ON a.id=c.account_id
                              WHERE c.id=?''', (contact_id,)).fetchone()
    if not contact:
        raise ValueError('Unknown contact.')
    signal = choose_signal(conn, contact['account_id'])
    if not signal:
        return {'subject': f'AI governance at {contact["company"]}', 'body': '',
                'warning': 'Add a human-reviewed, cited account signal before drafting. The app will not invent personalization.'}
    f = FRAMEWORKS[SIGNALS[signal['kind']][2]]
    opener = signal['summary'].rstrip('. ')
    body = (f"Hi {contact['first_name']},\n\n"
            f"I noticed this reported development: {opener}. "
            f"I wondered how {contact['company']} is approaching AI governance as these initiatives develop.\n\n"
            f"One question I would value your perspective on: {f['question']} "
            f"One area worth exploring is {f['value']}.\n\n"
            "Would a short conversation be useful?\n\n"
            "Best,\n[Your name]\n[Your company]\n[Business contact and opt-out information]")
    return {'subject': f'AI governance at {contact["company"]}', 'body': body,
            'warning': 'DRAFT ONLY. Check factual wording, legal context, company/role, and local email rules before use.',
            'source': signal['source_url'], 'framework': f['label'], 'framework_type': f['type'],
            'framework_note': f['caution'], 'framework_url': f['url']}


def csv_safe(value):
    """Prevent spreadsheet formula execution in exported user-supplied strings."""
    s = str(value if value is not None else '')
    return "'" + s if s.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else s


def lemlist_csv(conn):
    rows = conn.execute('''SELECT c.*, a.name AS company FROM contacts c
        JOIN accounts a ON a.id=c.account_id ORDER BY a.name, c.last_name''').fetchall()
    result = io.StringIO(newline='')
    writer = csv.writer(result)
    writer.writerow(['email','firstName','lastname','companyName','jobTitle','linkedinUrl',
                     'icebreaker','governanceFramework','researchSource','emailSubject','emailDraft'])
    count = 0
    for c in rows:
        if not export_eligible(conn, c):
            continue
        d = make_draft(conn, c['id'])
        if not d.get('body'):  # only sourced outreach
            continue
        values = [c['email'], c['first_name'], c['last_name'], c['company'], c['title'],
                  c['linkedin_url'], d['body'].split('\n\n')[1],
                  d['framework'], d['source'], d['subject'], d['body']]
        writer.writerow([csv_safe(v) for v in values])
        count += 1
    return result.getvalue(), count


ALIASES = {
  'company': ('company', 'companyName', 'account', 'account_name', 'Company Name'),
  'first': ('firstName', 'first_name', 'First Name', 'firstname'),
  'last': ('lastName', 'last_name', 'Last Name', 'lastname'),
  'title': ('jobTitle', 'title', 'Job Title', 'job_title'),
  'email': ('email', 'Email', 'workEmail', 'email_address'),
  'linkedin': ('linkedinUrl', 'linkedin_url', 'LinkedIn URL'),
  'industry': ('industry', 'Industry'), 'region': ('region', 'Region'),
  'source': ('dataSource', 'data_source', 'source'),
}


def _field(row, key):
    for alias in ALIASES[key]:
        if alias in row and row[alias]:
            return str(row[alias]).strip()
    return ''


def import_csv(conn, content):
    """CSV from Clay or user-owned CRM, NOT LinkedIn scraping. Re-imports never auto-approve."""
    if len(content.encode('utf-8')) > 1_000_000:
        raise ValueError('CSV is too large (maximum 1 MB).')
    reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
    if not reader.fieldnames:
        raise ValueError('CSV needs a header row.')
    if not any(c in reader.fieldnames for c in ALIASES['company']):
        raise ValueError('A company/companyName column is required.')
    added, skipped = 0, 0
    for n, row in enumerate(reader, start=1):
        if n > 500:
            raise ValueError('Import at most 500 rows at a time.')
        company = _field(row, 'company')
        first = _field(row, 'first')
        if not company or not first:
            skipped += 1
            continue
        email = _field(row, 'email')
        if email and not valid_email(email):
            skipped += 1
            continue
        acc_id = add_account(conn, company, _field(row, 'industry'), _field(row, 'region'))
        current = conn.execute('SELECT count(*) AS n FROM contacts WHERE account_id=? AND email=?',
                               (acc_id, email.strip().lower())).fetchone()['n']
        if current:  # including demo rows; preserve opt-outs and review state
            skipped += 1
            continue
        add_contact(conn, acc_id, first, _field(row, 'last'), _field(row, 'title'), email,
                    _field(row, 'linkedin'), _field(row, 'source') or 'User-provided CSV')
        added += 1
    return added, skipped


def seed_demo(conn):
    if conn.execute('SELECT count(*) FROM accounts').fetchone()[0]:
        return False
    from datetime import timedelta
    today = date.today()
    fixtures = [
        ('Northstar Financial Group', 'Financial services', 'UK / EU',
         ('Alex','Morgan','Head of AI Governance','alex.morgan@northstar.example'),
         [('governance_hire','Northstar has appointed a leader for its AI governance programme.'),
          ('regulatory_review','Northstar has announced an internal AI compliance review.')]),
        ('Aster Retail Holdings', 'Retail', 'United States',
         ('Jordan','Lee','VP Enterprise Risk','jordan.lee@aster.example'),
         [('ai_rollout','Aster plans to expand AI-enabled operational workflows.'),
          ('third_party_ai','Aster has discussed wider use of third-party AI tools.')]),
        ('Meridian Health Systems', 'Healthcare', 'EU',
         ('Sam','Taylor','Director, Responsible AI','sam.taylor@meridian.example'),
         [('iso_initiative','Meridian has started an internal AI management-system initiative.'),
          ('risk_framework','Meridian is exploring a structured AI risk framework.')]),
    ]
    for company, industry, region, person, signals in fixtures:
        a = add_account(conn, company, industry, region, notes='FICTIONAL DEMO ACCOUNT — not a real prospect')
        add_contact(conn, a, *person, data_source='Fictional demo data', verified=False, approved=False)
        for idx, (kind, summary) in enumerate(signals):
            add_signal(conn, a, kind, summary, f'https://example.com/demo/{company.lower().replace(" ", "-")}/{idx}',
                       (today-timedelta(days=10+idx*12)).isoformat(),
                       source_reviewed=not (company == 'Aster Retail Holdings' and kind == 'third_party_ai'))
    return True

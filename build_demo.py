"""Produce a completely static, isolated public demo from the tested Python domain model.
No uploaded contacts, SQLite database or server write endpoints are ever published.
"""
from __future__ import annotations
import json
import shutil
from datetime import date
from pathlib import Path
from core import connect, init_db, seed_demo, score_account, FRAMEWORKS, SIGNALS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'dist'

def main():
    OUT.mkdir(exist_ok=True)
    conn = connect(':memory:')
    try:
        init_db(conn)
        seed_demo(conn)
        accounts = []
        for a in conn.execute('SELECT * FROM accounts ORDER BY name'):
            signals = [dict(s) for s in conn.execute('SELECT * FROM signals WHERE account_id=? ORDER BY observed_on DESC', (a['id'],))]
            contacts = []
            for c in conn.execute('SELECT * FROM contacts WHERE account_id=?', (a['id'],)):
                # Minimize the public payload: no email, LinkedIn URL, notes, or private CRM fields.
                contacts.append({'id': c['id'], 'first': c['first_name'], 'last': c['last_name'],
                                 'role': c['title'], 'stage': c['stage'], 'verified': False,
                                 'approved': False, 'suppressed': bool(c['suppressed']),
                                 'held': False, 'firstDate': '', 'secondDate': ''})
            score, reasons = score_account(signals)
            accounts.append({'id': a['id'], 'name': a['name'], 'industry': a['industry'],
                             'region': a['region'], 'summary': a['notes'],
                             'score': score, 'reasons': reasons,
                             'signals': [{'id': s['id'], 'kind': s['kind'], 'summary': s['summary'],
                                          'url': s['source_url'], 'observed': s['observed_on'],
                                          'reviewed': bool(s['source_reviewed'])} for s in signals],
                             'contacts': contacts})
        payload = {'generated': date.today().isoformat(), 'fictional': True,
                   'frameworks': FRAMEWORKS, 'signalTypes': SIGNALS, 'accounts': accounts}
    finally:
        conn.close()
    (OUT/'health.json').write_text(json.dumps({'status':'ok','mode':'synthetic-static-demo'})+'\n', encoding='utf-8')
    (OUT/'data.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    shutil.copy2(ROOT/'demo'/'app.js', OUT/'app.js')
    shutil.copy2(ROOT/'demo'/'style.css', OUT/'style.css')
    shutil.copy2(ROOT/'demo'/'index.html', OUT/'index.html')
    print(f'Built static public demo: {len(accounts)} fictional accounts; no SQLite file')

if __name__ == '__main__': main()

"""AI Governance GTM Hub — local, dependency-free portfolio application.

Run: python app.py  (then visit http://127.0.0.1:8765)
"""
from __future__ import annotations

import csv
import io
import os
from datetime import date
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from core import (FRAMEWORKS, SIGNALS, STAGES, DEFAULT_DB, account_score, add_account,
                  add_contact, add_signal, connect, export_eligible, import_csv, init_db,
                  lemlist_csv, make_draft, qualified, score_account, seed_demo, suppress,
                  valid_email)

HOST, PORT = '127.0.0.1', int(os.environ.get('PORT', '8765'))
DB = os.environ.get('GTM_DB', str(DEFAULT_DB))
ROOT = Path(__file__).resolve().parent


def e(value):
    return escape(str(value if value is not None else ''), quote=True)


def anchor(href, label, cls=''):
    return f'<a class="{cls}" href="{e(href)}">{e(label)}</a>'


def options(items, selected=''):
    return ''.join(f'<option value="{e(value)}" {"selected" if selected == value else ""}>{e(label)}</option>'
                   for value, label in items)


def layout(title, content, notice='', warn=False):
    banner = f'<div class="notice {"danger" if warn else ""}">{e(notice)}</div>' if notice else ''
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} · GTM Intelligence Hub</title>
<link rel="stylesheet" href="/static/style.css"></head><body>
<aside class="side"><div class="brand"><span class="brand-icon">◎</span><div><b>AI Governance</b><small>GTM Intelligence Hub</small></div></div>
<nav><a href="/">▦ &nbsp; Overview</a><a href="/accounts">◈ &nbsp; Accounts</a><a href="/import">⇧ &nbsp; Import leads</a>
<a href="/export">⇥ &nbsp; Exports</a><a href="/guide">ⓘ &nbsp; Framework guide</a></nav>
<div class="sidefoot">Portfolio demo · Local-first<br>No paid tools or API keys required.</div></aside>
<main><header><div><span class="eyebrow">BDR RESEARCH WORKSPACE</span><h1>{e(title)}</h1></div>
<span class="top-pill">● LOCAL DEMO</span></header>{banner}{content}
<footer>Fictional starter data · Human review required · Not compliance or legal advice · No emails sent by this app.</footer>
</main></body></html>'''


def dashboard(conn):
    accounts = conn.execute('SELECT * FROM accounts ORDER BY name').fetchall()
    contacts = conn.execute('SELECT * FROM contacts').fetchall()
    monthly_qualified = sum(qualified(c) and c['first_meeting_date'].startswith(date.today().strftime('%Y-%m')) for c in contacts)
    metrics = {'accounts': len(accounts), 'contacts': len(contacts),
               'replied': sum(c['stage'] == 'Replied' for c in contacts),
               'first': sum(bool(c['first_meeting_held'] and c['first_meeting_date']) for c in contacts),
               'qualified': sum(qualified(c) for c in contacts), 'monthly':monthly_qualified}
    head = '''<section class="hero"><div><span class="eyebrow light">PORTFOLIO PROJECT</span>
<h2>From AI governance signals to qualified meetings.</h2>
<p>Prioritize accounts, map the EU AI Act / ISO 42001 / NIST AI RMF, write sourced outreach, and measure the BDR outcomes that matter.</p>
<a class="btn light" href="/accounts">Explore accounts →</a></div><div class="orb">◎</div></section>'''
    tiles = ''.join(f'<div class="metric"><span>{label}</span><strong>{metrics[key]}</strong><small>{sub}</small></div>'
                    for key, label, sub in [('accounts','Target accounts','Tracked'),('contacts','Stakeholders','Mapped'),
                                            ('replied','Positive / other replies','Stage marked Replied'),
                                            ('first','First meetings held','Confirmed'),('qualified','Qualified meetings','Second meeting booked'),('monthly','This month / target 4','First held + second booked')])
    rows=[]
    for a in sorted(accounts, key=lambda a: account_score(conn,a['id'])[0], reverse=True):
        score, why = account_score(conn,a['id'])
        n = conn.execute('SELECT count(*) FROM contacts WHERE account_id=?',(a['id'],)).fetchone()[0]
        rows.append(f'<tr><td><b>{anchor("/account?id="+str(a["id"]), a["name"])}</b><br><small>{e(a["industry"])} · {e(a["region"])}</small></td>'
                    f'<td><span class="score">{score}/100</span></td><td>{n}</td><td>{e("; ".join(why[:2]) or "Add reviewed signals")}</td></tr>')
    table = ('<table><thead><tr><th>Account</th><th>Opportunity score</th><th>Contacts</th><th>Why now?</th></tr></thead><tbody>'
             + ''.join(rows) + '</tbody></table>') if rows else '<p>No accounts yet. Add one to begin.</p>'
    explanation = '''<div class="info">↗ <b>What does “qualified” mean?</b> Following Enzai’s public BDR role: a first meeting that <b>took place</b> and resulted in a <b>second meeting booked</b>. Scores are account outreach priorities, never legal compliance ratings.</div>'''
    return head+f'<div class="metrics">{tiles}</div>'+explanation+f'<section class="panel"><div class="sectiontitle"><h2>Target account leaderboard</h2><a href="/accounts">Manage all →</a></div>{table}</section>'


def accounts_view(conn):
    accounts = conn.execute('SELECT * FROM accounts ORDER BY name').fetchall()
    blocks=[]
    for a in sorted(accounts,key=lambda a:account_score(conn,a['id'])[0],reverse=True):
        score, why = account_score(conn,a['id'])
        blocks.append(f'<article class="account-card"><div><span class="eyebrow">{e(a["industry"])} · {e(a["region"])}</span>'
                      f'<h3>{anchor("/account?id="+str(a["id"]),a["name"])}</h3><p>{e(" • ".join(why[:2]) or "No reviewed signals yet")}</p></div>'
                      f'<div class="right"><span class="score big">{score}/100</span>{anchor("/account?id="+str(a["id"]),"Open account →", "btn outline")}</div></article>')
    form='''<section class="panel"><div class="sectiontitle"><h2>Add target account</h2></div>
<form method="post" action="/add-account" class="formgrid">
<label>Company name*<input required maxlength="140" name="name" placeholder="Company name"></label>
<label>Industry<input name="industry" placeholder="Financial services"></label>
<label>Region<input name="region" placeholder="UK / EU"></label>
<label>Website URL<input name="website" placeholder="https://..."></label>
<label class="wide">Research notes<textarea name="notes" rows="2" placeholder="Why might this account be relevant?"></textarea></label>
<button class="btn" type="submit">Add account</button></form></section>'''
    return '<section class="panel"><div class="sectiontitle"><h2>Prioritized accounts</h2><a href="/import">Import leads →</a></div>'+''.join(blocks)+'</section>'+form


def account_view(conn, aid):
    a=conn.execute('SELECT * FROM accounts WHERE id=?',(aid,)).fetchone()
    if not a:
        raise ValueError('Account not found.')
    score, reasons=account_score(conn,aid)
    signals=conn.execute('SELECT * FROM signals WHERE account_id=? ORDER BY observed_on DESC',(aid,)).fetchall()
    people=conn.execute('SELECT * FROM contacts WHERE account_id=? ORDER BY first_name',(aid,)).fetchall()
    contact_rows=[]
    for c in people:
        flags = ' <span class="tag ok">Qualified</span>' if qualified(c) else ' <span class="tag">'+e(c['stage'])+'</span>'
        contact_rows.append(f'<tr><td><b>{anchor("/contact?id="+str(c["id"]),c["first_name"]+" "+c["last_name"])}</b>{flags}'
                            f'<br><small>{e(c["title"])}</small></td><td>{e(c["email"] or "Not provided")}</td>'
                            f'<td>{"Yes" if c["verified"] else "No"}</td><td>{anchor("/contact?id="+str(c["id"]),"Details →")}</td></tr>')
    sigs=[]
    for s in signals:
        label,_,fkey=SIGNALS[s['kind']]
        f=FRAMEWORKS[fkey]
        review_action = (f'<form action="/review-signal" method="post"><input type="hidden" name="signal_id" value="{s["id"]}"><button type="submit" class="btn outline">Mark source reviewed</button></form>' if not s['source_reviewed'] else '')
        sigs.append(f'''<div class="signal"><div><span class="tag">{e(label)}</span>
        <span class="tag {"ok" if s["source_reviewed"] else ""}">{"Human-reviewed" if s["source_reviewed"] else "Unreviewed"}</span>
        <p>{e(s['summary'])}</p><small>{e(s['observed_on'])} · <a href="{e(s['source_url'])}" target="_blank" rel="noopener noreferrer">Evidence ↗</a>
        · {e(f['label'])} ({e(f['type'])})</small>{review_action}</div></div>''')
    sig_opts=options([(k,v[0]) for k,v in SIGNALS.items()])
    contact_form=f'''<section class="panel"><h2>Add decision-maker</h2><p class="muted">Use permitted research/CRM sources. Never auto-export scraped LinkedIn profiles.</p>
<form action="/add-contact" method="post" class="formgrid"><input type="hidden" name="account_id" value="{aid}">
<label>First name*<input name="first_name" required></label><label>Last name<input name="last_name"></label>
<label>Job title<input name="title" placeholder="Head of AI Governance"></label><label>Work email<input name="email" type="email"></label>
<label>LinkedIn profile URL<input name="linkedin_url" type="url"></label><label>Permitted data source<input name="data_source" placeholder="Company website / authorized CRM"></label>
<button class="btn" type="submit">Add stakeholder</button></form></section>'''
    signal_form=f'''<section class="panel"><h2>Add researched buying signal</h2>
<form action="/add-signal" method="post" class="formgrid"><input type="hidden" name="account_id" value="{aid}">
<label>Signal category<select name="kind">{sig_opts}</select></label><label>Observed date<input name="observed_on" type="date" value="{date.today().isoformat()}" required></label>
<label class="wide">Evidence URL*<input name="source_url" required type="url" placeholder="https://company.com/news/..."></label>
<label class="wide">What did the source actually say?*<textarea name="summary" required maxlength="600" rows="2" placeholder="Company announced..."></textarea></label>
<label class="checkbox wide"><input name="source_reviewed" type="checkbox" value="yes"> I personally checked the source and the summary is accurate.</label>
<button class="btn" type="submit">Save buying signal</button></form></section>'''
    return (f'<div class="info"><b>{e(a["name"])} — opportunity score {score}/100.</b> {e("; ".join(reasons) or "No reviewed evidence yet.")}<br><small>{e(a["notes"])}</small></div>'
            +'<section class="panel"><div class="sectiontitle"><h2>Buying signals and framework context</h2></div>'+(''.join(sigs) or '<p>No signals yet.</p>')+'</section>'
            +'<section class="panel"><h2>Buying committee</h2><div class="responsive"><table><thead><tr><th>Stakeholder</th><th>Work email</th><th>Email reviewed?</th><th></th></tr></thead><tbody>'
            +''.join(contact_rows)+'</tbody></table></div></section>' + signal_form + contact_form)


def contact_view(conn, cid):
    c=conn.execute('SELECT c.*, a.name AS company FROM contacts c JOIN accounts a ON a.id=c.account_id WHERE c.id=?',(cid,)).fetchone()
    if not c:
        raise ValueError('Contact not found.')
    draft=make_draft(conn,cid)
    verified='checked' if c['verified'] else ''
    approved='checked' if c['approved'] else ''
    optout='checked' if c['suppressed'] else ''
    held='checked' if c['first_meeting_held'] else ''
    o=options([(s,s) for s in STAGES],c['stage'])
    eligible=export_eligible(conn,c) and bool(draft.get('body'))
    status=f'<span class="tag {"ok" if eligible else ""}">{"Eligible for reviewed CSV export" if eligible else "Excluded from outbound export"}</span>'
    details=f'''<section class="panel"><div class="sectiontitle"><h2>{e(c['first_name'])} {e(c['last_name'])}</h2>{status}</div>
<p><b>{e(c['title'])}</b> · {e(c['company'])}<br><small>{e(c['email'] or 'Email not provided')} · Source: {e(c['data_source'] or 'not recorded')}</small></p>
<form action="/update-contact" method="post" class="formgrid"><input type="hidden" name="contact_id" value="{cid}">
<label>Outreach stage<select name="stage">{o}</select></label><label>First meeting date (scheduled/held)<input type="date" name="first_meeting_date" value="{e(c['first_meeting_date'])}"></label>
<label>Second meeting booked for<input type="date" name="second_meeting_date" value="{e(c['second_meeting_date'])}"></label>
<label class="checkbox"><input type="checkbox" name="first_meeting_held" value="yes" {held}> First meeting actually took place</label>
<label class="checkbox wide"><input type="checkbox" name="verified" value="yes" {verified}> I checked the work email; it is deliverable and correctly attributed.</label>
<label class="checkbox wide"><input type="checkbox" name="approved" value="yes" {approved}> Outbound use reviewed for lawful basis, source transparency, and jurisdictional rules.</label>
<label class="checkbox wide"><input type="checkbox" name="suppressed" value="yes" {optout}> Do not contact / opted out (cannot be reversed by this form)</label>
<button class="btn" type="submit">Save CRM record</button></form></section>'''
    draft_section = (f'<section class="panel"><h2>Evidence-led outbound draft</h2><p class="muted">Subject: <b>{e(draft["subject"])}</b></p>'
                     + (f'<pre class="draft">{e(draft["body"])}</pre><p><small>Research source: {anchor(draft["source"], draft["source"])} · {e(draft["framework"])} ({e(draft["framework_type"])})</small></p>'
                        f'<div class="info">{e(draft["framework_note"])}</div>' if draft.get('body') else '')
                     +f'<p class="muted">{e(draft["warning"])}</p></section>')
    return details + draft_section


def importer():
    example='companyName,firstName,lastName,jobTitle,email,linkedinUrl,industry,region,dataSource\nExample Enterprise,Jane,Doe,Head of AI Governance,jane.doe@example.com,,Technology,United Kingdom,Permitted CRM'
    return f'''<div class="info">Paste a Clay-enriched CSV or an authorized CRM export. Imported contacts are <b>unapproved</b> until you validate email and outreach permissions. No LinkedIn scraping or live data harvesting.</div>
<section class="panel"><h2>Import contacts from CSV</h2><p class="muted">Supports columns companyName, firstName, lastName, jobTitle, email, linkedinUrl, industry, region and dataSource (plus common aliases). Maximum 500 rows / 1 MB.</p>
<form action="/import" method="post"><label>Choose a local .csv file (processed in this browser)</label><input type="file" id="csvfile" accept=".csv,text/csv">
<label>CSV text<textarea name="csv_text" id="csv_text" rows="9" placeholder="companyName,firstName,..." required></textarea></label>
<button class="btn" type="submit">Import account and contacts</button></form>
<details><summary>Show sample CSV format</summary><pre class="draft">{e(example)}</pre></details></section>
<script>document.getElementById('csvfile').addEventListener('change',async function(){{if(this.files[0])document.getElementById('csv_text').value=await this.files[0].text()}});</script>'''


def export_view(conn):
    csv_text, cnt=lemlist_csv(conn)
    people=conn.execute('SELECT * FROM contacts').fetchall()
    return f'''<section class="panel"><h2>lemlist-ready campaign CSV</h2>
<div class="exportnum">{cnt} <span>contacts ready for export</span></div>
<p>Includes lemlist-compatible fields such as <code>email</code>, <code>firstName</code>, <code>companyName</code>, and custom outreach fields. Confirm field mappings in lemlist on import.</p>
<p><b>Safety checks:</b> verified email, human-reviewed outreach permission, non-demo address, no opt-out, and at least one reviewed research signal.</p>
<a class="btn" href="/download/lemlist">Download lemlist CSV ↓</a><div class="info">The app prepares files only: it does not send emails or create campaigns in lemlist. Check the campaign preview before sending.</div></section>
<section class="panel"><h2>CRM activity CSV</h2><p>Export all contact stages, account scores, and meeting outcomes, including the exact qualified-meeting definition.</p>
<a class="btn outline" href="/download/crm">Download CRM report ↓</a></section>
<section class="panel"><h2>How to use the stack</h2>
<ol><li><b>Sales Navigator:</b> Identify target firms, professional roles and possible introduction routes. Enter contacts through authorized channels.</li>
<li><b>Clay:</b> Enrich permitted records and research cited buying signals. Export a CSV for this application.</li>
<li><b>This app:</b> Score accounts, map governance themes, draft sourced messages, and track meetings.</li>
<li><b>lemlist:</b> Import the approved CSV, map fields, check sender setup and stop rules, preview, then launch separately.</li></ol></section>'''


def guide():
    frameworks=''.join(f'''<article class="framework"><div class="sectiontitle"><h2>{e(v['label'])}</h2><span class="tag">{e(v['type'])}</span></div>
<p><b>BDR discovery angle:</b> {e(v['question'])}</p><p><b>Product-relevance hypothesis:</b> {e(v['value'])}.</p>
<p class="muted">{e(v['caution'])}</p><a href="{e(v['url'])}" target="_blank" rel="noopener noreferrer">Official source ↗</a></article>'''
                   for v in FRAMEWORKS.values())
    return '''<div class="info">A buying signal is evidence to prioritize a conversation, not a compliance finding. Especially with the EU AI Act, verify current law, applicability, actor role, and application dates before making specific claims.</div>
<section class="panel"><h2>The three frameworks</h2>'''+frameworks+'''</section><section class="panel"><h2>Responsible outbound checklist</h2>
<ul><li>Use company-published news, permitted prospect data, and authorized CRM/Clay workflows.</li>
<li>Review each source yourself; evidence URLs are not automatically fact-checked.</li>
<li>Do not infer violations, certification, compliance status or a confirmed budget.</li>
<li>Record the legal basis and required privacy notice; handle objections and suppression across tools.</li>
<li>Follow laws where prospects are located; UK PECR and UK GDPR rules are not identical.</li>
<li>Review opt-out details and email-sender authentication before importing into an outreach platform.</li>
</ul><p><a href="https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/business-to-business-marketing/" target="_blank" rel="noopener noreferrer">UK ICO B2B marketing guidance ↗</a> · <a href="https://www.linkedin.com/help/sales-navigator/answer/a1339701" target="_blank" rel="noopener noreferrer">LinkedIn's rules on third-party tools ↗</a></p></section>'''


def safe_spreadsheet(value):
    s=str(value if value is not None else '')
    return "'"+s if s.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else s


def crm_csv(conn):
    out=io.StringIO(newline='')
    writer=csv.writer(out)
    writer.writerow(['company','priorityScore','contact','jobTitle','email','stage','firstMeetingHeld','firstMeetingDate','secondMeetingDate','qualifiedMeeting'])
    for c in conn.execute('SELECT c.*, a.name AS company FROM contacts c JOIN accounts a ON a.id=c.account_id ORDER BY a.name'):
        w=[c['company'],account_score(conn,c['account_id'])[0],c['first_name']+' '+c['last_name'],c['title'],c['email'],c['stage'],
           int(c['first_meeting_held']),c['first_meeting_date'],c['second_meeting_date'],int(qualified(c))]
        writer.writerow([safe_spreadsheet(x) for x in w])
    return out.getvalue()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self._local_request():
            self.send_error(403,'Local workspace only');return
        p=urlparse(self.path)
        q=parse_qs(p.query)
        if p.path=='/static/style.css':
            b=(ROOT/'static'/'style.css').read_bytes()
            self.send_response(200);self.send_header('Content-Type','text/css; charset=utf-8')
            self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
        conn=connect(DB)
        try:
            if p.path in ('/download/lemlist','/download/crm'):
                content = lemlist_csv(conn)[0] if p.path.endswith('lemlist') else crm_csv(conn)
                name = 'lemlist-approved-leads.csv' if p.path.endswith('lemlist') else 'bdr-crm-outcomes.csv'
                b=content.encode('utf-8-sig');self.send_response(200)
                self.send_header('Content-Type','text/csv; charset=utf-8')
                self.send_header('Content-Disposition',f'attachment; filename="{name}"')
                self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
            if p.path=='/': title,body='Overview',dashboard(conn)
            elif p.path=='/accounts': title,body='Target accounts',accounts_view(conn)
            elif p.path=='/account':
                aid=int(q.get('id',['0'])[0]);
                a=conn.execute('SELECT name FROM accounts WHERE id=?',(aid,)).fetchone()
                title,body=(a['name'] if a else 'Account'),account_view(conn,aid)
            elif p.path=='/contact':
                cid=int(q.get('id',['0'])[0]);
                c=conn.execute('SELECT first_name,last_name FROM contacts WHERE id=?',(cid,)).fetchone()
                title,body=(c['first_name']+' '+c['last_name'] if c else 'Contact'),contact_view(conn,cid)
            elif p.path=='/import': title,body='Import leads',importer()
            elif p.path=='/export': title,body='Export and integrations',export_view(conn)
            elif p.path=='/guide': title,body='AI governance guide',guide()
            else: self.send_error(404,'Not found');return
            self.send_html(layout(title,body,q.get('msg',[''])[0],q.get('error',[''])[0]=='1'))
        except (ValueError,KeyError) as ex:
            self.send_html(layout('Error',f'<div class="notice danger">{e(ex)}</div><p>{anchor("/", "← Back to overview")}</p>'),status=400)
        finally:
            conn.close()

    def send_html(self,html,status=200):
        b=html.encode('utf-8');self.send_response(status)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(b)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self' 'unsafe-inline'; img-src 'self'; base-uri 'none'; form-action 'self'")
        self.end_headers();self.wfile.write(b)

    def _local_request(self):
        host = self.headers.get('Host', '').split(':')[0].lower()
        return host in ('127.0.0.1', 'localhost', '[::1]')

    def do_POST(self):
        if not self._local_request():
            self.send_error(403, 'Local workspace only');return
        origin = self.headers.get('Origin', '') or self.headers.get('Referer', '')
        if origin:
            source = urlparse(origin)
            allowed = source.scheme == 'http' and source.hostname in ('127.0.0.1', 'localhost') and source.port == PORT
            if not allowed:
                self.send_error(403, 'Cross-origin form submissions are blocked');return
        try: n=int(self.headers.get('Content-Length','0'))
        except ValueError: self.send_error(400,'Invalid payload size');return
        if n <= 0:
            self.send_error(400,'Empty payload');return
        if n>1_250_000:
            self.send_error(413,'Payload too large');return
        if 'application/x-www-form-urlencoded' not in self.headers.get('Content-Type',''):
            self.send_error(415,'Unsupported form encoding');return
        form={k:v[0] for k,v in parse_qs(self.rfile.read(n).decode('utf-8','replace'),keep_blank_values=True).items()}
        path=urlparse(self.path).path
        conn=connect(DB);back='/'
        try:
            if path=='/add-account':
                aid=add_account(conn,form.get('name',''),form.get('industry',''),form.get('region',''),form.get('website',''),form.get('notes',''))
                back=f'/account?id={aid}';message='Account saved.'
            elif path=='/add-contact':
                aid=int(form['account_id']);add_contact(conn,aid,form.get('first_name',''),form.get('last_name',''),form.get('title',''),
                  form.get('email',''),form.get('linkedin_url',''),form.get('data_source',''))
                back=f'/account?id={aid}';message='Contact saved. Verify and approve before outreach export.'
            elif path=='/add-signal':
                aid=int(form['account_id']);add_signal(conn,aid,form.get('kind',''),form.get('summary',''),form.get('source_url',''),
                          form.get('observed_on',''),form.get('source_reviewed')=='yes')
                back=f'/account?id={aid}';message='Buying signal saved.'
            elif path=='/review-signal':
                sid=int(form['signal_id'])
                signal=conn.execute('SELECT account_id FROM signals WHERE id=?',(sid,)).fetchone()
                if not signal: raise ValueError('Signal not found')
                back=f'/account?id={signal["account_id"]}'
                conn.execute('UPDATE signals SET source_reviewed=1 WHERE id=?',(sid,));conn.commit()
                message='Source marked human-reviewed. Ensure you actually checked its evidence.'
            elif path=='/update-contact':
                cid=int(form['contact_id']);back=f'/contact?id={cid}'
                c=conn.execute('SELECT * FROM contacts WHERE id=?',(cid,)).fetchone()
                if not c: raise ValueError('Contact not found')
                stage=form.get('stage','New')
                if stage not in STAGES: raise ValueError('Invalid stage')
                first_date=form.get('first_meeting_date','')
                second_date=form.get('second_meeting_date','')
                for d in (first_date,second_date):
                    if d: date.fromisoformat(d)
                if form.get('first_meeting_held')=='yes' and not first_date:
                    raise ValueError('Enter the date of the first meeting before marking it held.')
                if first_date and form.get('first_meeting_held')=='yes' and date.fromisoformat(first_date)>date.today():
                    raise ValueError('A meeting cannot be marked held on a future date.')
                if second_date and first_date and date.fromisoformat(second_date)<=date.fromisoformat(first_date):
                    raise ValueError('Second meeting date must be after the first meeting.')
                if second_date and not form.get('first_meeting_held')=='yes':
                    raise ValueError('Mark the first meeting held before recording a second meeting.')
                opted_out=bool(c['suppressed']) or form.get('suppressed')=='yes'
                conn.execute('''UPDATE contacts SET stage=?,first_meeting_date=?,first_meeting_held=?,second_meeting_date=?,
                 verified=?,approved=?,suppressed=? WHERE id=?''',
                 (stage,first_date,int(form.get('first_meeting_held')=='yes'),second_date,
                  int(form.get('verified')=='yes'),int(form.get('approved')=='yes'),int(opted_out),cid))
                if opted_out and c['email']:
                    suppress(conn,c['email'])
                conn.commit();message='Contact and meeting outcomes updated.'
            elif path=='/import':
                back='/import';added,skipped=import_csv(conn,form.get('csv_text',''))
                message=f'Imported {added} new contact(s); skipped {skipped} incomplete/duplicate row(s).'
            else: self.send_error(404);return
            self.redirect(back,message)
        except (ValueError,KeyError, __import__('sqlite3').IntegrityError) as ex:
            self.redirect(back,str(ex),True)
        finally: conn.close()

    def redirect(self,path,message,is_error=False):
        glue='&' if '?' in path else '?'
        where=path+glue+urlencode({'msg':message,'error':int(is_error)})
        self.send_response(303);self.send_header('Location',where);self.end_headers()


if __name__=='__main__':
    with connect(DB) as conn:
        init_db(conn)
        if seed_demo(conn):
            print('Seeded fictional demonstration data (clearly marked, not real prospects).')
    print(f'AI Governance GTM Hub → http://{HOST}:{PORT}')
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

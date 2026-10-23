"""Run with: python -m unittest discover -s tests -v"""
import csv
import io
import tempfile
import unittest
from unittest.mock import patch
from datetime import date, timedelta
from pathlib import Path

from core import (SIGNALS, add_account, add_contact, add_signal, connect, csv_safe,
                  export_eligible, import_csv, init_db, lemlist_csv, make_draft,
                  qualified, score_account, seed_demo, suppress, valid_http_url)


class HubTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / 'test.db')
        init_db(self.db)
        self.account = add_account(self.db, 'Test Enterprise', 'Finance', 'United Kingdom')
        self.contact_id = add_contact(self.db, self.account, 'Jane', 'Smith', 'Head of AI Governance',
                                      'jane.smith@research.test', data_source='Approved CRM')

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def signal(self, reviewed=True, kind='governance_hire', summary='Test Enterprise appointed an AI governance lead'):
        add_signal(self.db, self.account, kind, summary, 'https://news.example.com/announcement',
                   (date.today() - timedelta(days=12)).isoformat(), reviewed)

    def test_signal_priority_requires_human_review(self):
        self.signal(reviewed=False)
        signals = self.db.execute('SELECT * FROM signals').fetchall()
        self.assertEqual(score_account(signals)[0], 0)
        self.db.execute('UPDATE signals SET source_reviewed=1')
        self.db.commit()
        self.assertEqual(score_account(self.db.execute('SELECT * FROM signals').fetchall())[0], 27)

    def test_draft_requires_evidence(self):
        self.assertFalse(make_draft(self.db, self.contact_id)['body'])
        self.signal(reviewed=True)
        result = make_draft(self.db, self.contact_id)
        self.assertIn('Test Enterprise', result['body'])
        self.assertIn('ISO/IEC 42001', result['framework'])
        self.assertIn('https://news.example.com/announcement', result['source'])

    def test_lemlist_export_gates_and_headers(self):
        self.signal()
        self.assertEqual(lemlist_csv(self.db)[1], 0)  # unreviewed contact is blocked
        self.db.execute('UPDATE contacts SET verified=1, approved=1')
        self.db.commit()
        with patch('core.demo_email', return_value=False):  # isolate approval path using reserved test addresses
            raw, count = lemlist_csv(self.db)
        self.assertEqual(count, 1)
        rows = list(csv.DictReader(io.StringIO(raw)))
        self.assertEqual(rows[0]['firstName'], 'Jane')
        self.assertEqual(rows[0]['companyName'], 'Test Enterprise')
        self.assertTrue(rows[0]['emailDraft'])

    def test_suppression_survives_reviewed_contact(self):
        self.signal()
        self.db.execute('UPDATE contacts SET verified=1, approved=1')
        self.db.commit()
        c = self.db.execute('SELECT * FROM contacts WHERE id=?', (self.contact_id,)).fetchone()
        with patch('core.demo_email', return_value=False):  # test suppression beyond demo-address rejection
            self.assertTrue(export_eligible(self.db, c))
            suppress(self.db, 'jane.smith@research.test')
            self.db.execute('UPDATE contacts SET suppressed=0')  # can't override global suppression
            self.db.commit()
            c = self.db.execute('SELECT * FROM contacts WHERE id=?', (self.contact_id,)).fetchone()
            self.assertFalse(export_eligible(self.db, c))
            self.assertEqual(lemlist_csv(self.db)[1], 0)

    def test_demo_addresses_never_export(self):
        self.signal()
        cid = add_contact(self.db, self.account, 'Demo', 'Person', email='demo@portfolio.example',
                          verified=True, approved=True)
        c = self.db.execute('SELECT * FROM contacts WHERE id=?', (cid,)).fetchone()
        self.assertFalse(export_eligible(self.db, c))

    def test_reserved_addresses_always_block_export(self):
        from core import demo_email
        for email in ('person@sub.example.com','person@company.test',
                      'person@company.invalid','person@work.localhost','person@org.example'):
            self.assertTrue(demo_email(email),email)
            self.signal(reviewed=True)
            c_id=add_contact(self.db,self.account,'Sample','Person',email=email,
                             verified=True,approved=True)
            record=self.db.execute('SELECT * FROM contacts WHERE id=?',(c_id,)).fetchone()
            self.assertFalse(export_eligible(self.db,record))

    def test_meeting_qualified_definition(self):
        c = self.db.execute('SELECT * FROM contacts WHERE id=?', (self.contact_id,)).fetchone()
        self.assertFalse(qualified(c))
        self.db.execute('UPDATE contacts SET first_meeting_held=1,first_meeting_date=? WHERE id=?',
                        (date.today().isoformat(), self.contact_id))
        self.db.commit()
        c = self.db.execute('SELECT * FROM contacts WHERE id=?', (self.contact_id,)).fetchone()
        self.assertFalse(qualified(c))
        self.db.execute('UPDATE contacts SET second_meeting_date=? WHERE id=?',
                        ((date.today() + timedelta(days=7)).isoformat(), self.contact_id))
        self.db.commit()
        c = self.db.execute('SELECT * FROM contacts WHERE id=?', (self.contact_id,)).fetchone()
        self.assertTrue(qualified(c))

    def test_csv_import_dedup_preserves_review(self):
        self.db.execute('UPDATE contacts SET verified=1, approved=1')
        self.db.commit()
        csv_text = ('companyName,firstName,lastName,jobTitle,email\n'
                    'Test Enterprise,Jane,Smith,Head of AI Governance,jane.smith@research.test\n'
                    'New Company,Sam,Lee,CISO,sam.lee@newco.test\n')
        n, skipped = import_csv(self.db, csv_text)
        self.assertEqual((n, skipped), (1, 1))
        c = self.db.execute('SELECT * FROM contacts WHERE email=?', ('jane.smith@research.test',)).fetchone()
        self.assertEqual(c['approved'], 1)
        new = self.db.execute('SELECT * FROM contacts WHERE email=?', ('sam.lee@newco.test',)).fetchone()
        self.assertEqual(new['approved'], 0)

    def test_source_validation(self):
        self.assertFalse(valid_http_url('javascript:alert(1)'))
        with self.assertRaises(ValueError):
            add_signal(self.db, self.account, 'ai_rollout', 'New AI deployment', 'data:text/html,evil')
        with self.assertRaises(ValueError):
            add_signal(self.db, self.account, 'ai_rollout', 'Future event', 'https://example.com',
                       (date.today() + timedelta(days=1)).isoformat())

    def test_formula_injection_guard(self):
        self.assertTrue(csv_safe('=HYPERLINK("evil")').startswith("'"))
        self.assertEqual(csv_safe('An ordinary enterprise'), 'An ordinary enterprise')

    def test_suppression_preexists_contact_import(self):
        suppress(self.db,'new.person@domain.test')
        n, ignored=import_csv(self.db,'companyName,firstName,email\nTest Enterprise,New,new.person@domain.test\n')
        self.assertEqual((n,ignored),(1,0))
        c=self.db.execute('SELECT * FROM contacts WHERE email=?',('new.person@domain.test',)).fetchone()
        self.assertTrue(c['suppressed'])
        self.assertFalse(export_eligible(self.db,c))

    def test_date_qualification_rejects_corrupt_outcomes(self):
        self.db.execute('UPDATE contacts SET first_meeting_held=1,first_meeting_date=?,second_meeting_date=?',
                        ((date.today()+timedelta(days=5)).isoformat(),(date.today()+timedelta(days=9)).isoformat()))
        self.db.commit()
        self.assertFalse(qualified(self.db.execute('SELECT * FROM contacts').fetchone()))

    def test_urls_block_localhost_private_networks_and_backslashes(self):
        for u in ('http://127.0.0.1/admin','https://localhost','http://192.168.0.1',
                  'https://example.com\\@bad.example','javascript:alert(1)'):
            self.assertFalse(valid_http_url(u),u)
        self.assertTrue(valid_http_url('https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai'))

    def test_duplicate_add_contact_returns_original_identifier(self):
        again=add_contact(self.db,self.account,'Jane','Smith','Head of AI Governance',
                          'jane.smith@research.test')
        self.assertEqual(again,self.contact_id)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM contacts').fetchone()[0],1)

    def test_seed_demonstrates_but_does_not_allow_sends(self):
        other = connect(Path(self.temp.name) / 'demo.db')
        init_db(other)
        self.assertTrue(seed_demo(other))
        self.assertFalse(seed_demo(other))
        self.assertEqual(other.execute('SELECT COUNT(*) FROM accounts').fetchone()[0], 3)
        self.assertEqual(lemlist_csv(other)[1], 0)
        other.close()


if __name__ == '__main__':
    unittest.main()

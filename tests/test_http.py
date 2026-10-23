"""Local-only HTTP contract tests; no external network or third-party imports."""
import http.client
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode

import app
from core import connect, init_db, seed_demo

class LocalHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.original_db = app.DB
        cls.db_path = Path(cls.temporary.name) / 'http-test.db'
        app.DB = str(cls.db_path)
        c = connect(cls.db_path); init_db(c); seed_demo(c); c.close()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=3)
        app.DB = cls.original_db
        cls.temporary.cleanup()

    def request(self, method, path, body=None, extra_headers=None):
        headers={'Host': f'127.0.0.1:{self.server.server_port}'}
        if body is not None: headers['Content-Type']='application/x-www-form-urlencoded'
        headers.update(extra_headers or {})
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        connection.request(method, path, body=body, headers=headers)
        response=connection.getresponse(); status=response.status; payload=response.read()
        connection.close(); return status,payload

    def test_local_main_routes_render_and_escape(self):
        for route, phrase in [('/',b'Overview'),('/accounts',b'Northstar'),('/account?id=1',b'Buying signals'),
                              ('/guide',b'ISO/IEC 42001'),('/import',b'Import contacts'),('/export',b'lemlist-ready')]:
            status, content=self.request('GET',route)
            self.assertEqual(status,200,route)
            self.assertIn(phrase,content,route)

    def test_invalid_account_returns_400(self):
        self.assertEqual(self.request('GET','/account?id=99999')[0],400)

    def test_forged_host_is_denied(self):
        self.assertEqual(self.request('GET','/',extra_headers={'Host':'attacker.example'})[0],403)

    def test_cross_origin_form_post_is_denied(self):
        body=urlencode({'name':'Unauthorized Company'})
        status,_=self.request('POST','/add-account',body,{'Origin':'https://unrelated.example'})
        self.assertEqual(status,403)
        c=connect(self.db_path)
        self.assertFalse(c.execute('SELECT 1 FROM accounts WHERE name=?',('Unauthorized Company',)).fetchone())
        c.close()

    def test_same_local_origin_accepts_contact_form(self):
        body=urlencode({'name':'Authorized Test Company','industry':'Testing'})
        status,_=self.request('POST','/add-account',body)
        self.assertEqual(status,303)
        c=connect(self.db_path)
        self.assertTrue(c.execute('SELECT 1 FROM accounts WHERE name=?',('Authorized Test Company',)).fetchone())
        c.close()

    def test_request_payload_limit(self):
        # Verify pre-body rejection without transmitting >1 MB that could race a
        # server-side early close (BrokenPipe varies by Python/OS version).
        connection=http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            connection.putrequest('POST','/import')
            connection.putheader('Content-Length','1250001')
            connection.putheader('Content-Type','application/x-www-form-urlencoded')
            connection.endheaders()
            response=connection.getresponse()
            self.assertEqual(response.status,413)
            response.read()
        finally:
            connection.close()

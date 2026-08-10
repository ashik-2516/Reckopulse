import unittest
import json
import sqlite3
import tempfile
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app
from backend.database.db import DatabaseManager
from backend.api.routes import sanitize_input_text, ip_request_history

class TestPass10Security(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        ip_request_history.clear()

        self.tf = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tf.name
        self.tf.close()
        self.db_mgr = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except Exception:
            pass

    def test_input_sanitization_escapes_script_tags(self):
        malicious_input = "<script>alert('xss')</script>"
        sanitized = sanitize_input_text(malicious_input)
        self.assertEqual(sanitized, "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;")

        legitimate_input = "  men's denim jacket  "
        sanitized_legit = sanitize_input_text(legitimate_input)
        self.assertIn("men&#x27;s denim jacket", sanitized_legit)

    def test_sqlite_hot_backup_engine_creates_queryable_backup(self):
        # 1. Populate database with test records
        self.db_mgr.log_event("sess-backup-1", "aura_threads", "click", "CLOTH-101")
        self.db_mgr.add_merchant_rule("rule-backup-1", "aura_threads", "CLOTH-101", 30.0)

        # 2. Perform live online hot backup
        backup_tf = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        backup_path = backup_tf.name
        backup_tf.close()

        success = self.db_mgr.create_backup(backup_path)
        self.assertTrue(success)

        # 3. Verify backup database integrity and queryability
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events WHERE session_id = 'sess-backup-1'")
        event_count = cursor.fetchone()[0]
        self.assertEqual(event_count, 1)

        cursor.execute("SELECT boost_percent FROM merchant_rules WHERE rule_id = 'rule-backup-1'")
        boost = cursor.fetchone()[0]
        self.assertEqual(boost, 30.0)
        conn.close()

        try:
            os.remove(backup_path)
        except Exception:
            pass

    def test_rate_limiter_throttles_excessive_requests(self):
        # Simulate 100 rapid health check requests
        for _ in range(100):
            res = self.app.get('/api/health')
            self.assertEqual(res.status_code, 200)

        # 101st request from same IP should trigger HTTP 429
        res_throttled = self.app.get('/api/health')
        self.assertEqual(res_throttled.status_code, 429)
        data = json.loads(res_throttled.data)
        self.assertTrue(data.get('error'))
        self.assertEqual(data.get('code'), 'TOO_MANY_REQUESTS')

if __name__ == '__main__':
    unittest.main()

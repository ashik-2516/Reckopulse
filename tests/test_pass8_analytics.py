import unittest
import json
import sys
import os
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.db import DatabaseManager

class TestPass8Analytics(unittest.TestCase):
    def setUp(self):
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

    def test_zero_events_returns_zero_ratios_no_exception(self):
        analytics = self.db_mgr.get_event_analytics("empty_store")
        self.assertEqual(analytics['store_id'], "empty_store")
        self.assertEqual(analytics['conversion_ratios']['ctr_percent'], 0.0)
        self.assertEqual(analytics['conversion_ratios']['cart_conversion_percent'], 0.0)
        self.assertEqual(analytics['conversion_ratios']['purchase_conversion_percent'], 0.0)
        self.assertEqual(analytics['funnel']['impressions'], 0)

    def test_full_funnel_and_conversion_ratios(self):
        store_id = "test_store_funnel"
        session_id = "sess-funnel-1"

        # Log 100 Impressions, 20 Clicks, 10 Cart Adds, 5 Purchases
        for _ in range(100):
            self.db_mgr.log_event(session_id, store_id, "impression", "PROD-1")
        for _ in range(20):
            self.db_mgr.log_event(session_id, store_id, "click", "PROD-1", metadata={"reason_type": "trend"})
        for _ in range(10):
            self.db_mgr.log_event(session_id, store_id, "add_to_cart", "PROD-1", metadata={"reason_type": "trend"})
        for _ in range(5):
            self.db_mgr.log_event(session_id, store_id, "purchase", "PROD-1", metadata={"reason_type": "trend"})

        analytics = self.db_mgr.get_event_analytics(store_id)
        funnel = analytics['funnel']
        ratios = analytics['conversion_ratios']

        self.assertEqual(funnel['impressions'], 100)
        self.assertEqual(funnel['clicks'], 20)
        self.assertEqual(funnel['cart_adds'], 10)
        self.assertEqual(funnel['purchases'], 5)

        self.assertAlmostEqual(ratios['ctr_percent'], 20.0, places=1)
        self.assertAlmostEqual(ratios['cart_conversion_percent'], 50.0, places=1)
        self.assertAlmostEqual(ratios['purchase_conversion_percent'], 50.0, places=1)
        self.assertAlmostEqual(ratios['overall_conversion_percent'], 5.0, places=1)

    def test_signal_attribution_breakdown(self):
        store_id = "test_store_attribution"
        session_id = "sess-attrib-1"

        self.db_mgr.log_event(session_id, store_id, "click", "PROD-1", metadata={"reason_type": "collaborative"})
        self.db_mgr.log_event(session_id, store_id, "click", "PROD-2", metadata={"reason_type": "trend"})
        self.db_mgr.log_event(session_id, store_id, "click", "PROD-2", metadata={"reason_type": "trend"})

        analytics = self.db_mgr.get_event_analytics(store_id)
        attrib = analytics['signal_attribution']

        self.assertEqual(attrib['collaborative'], 1)
        self.assertEqual(attrib['trend'], 2)

if __name__ == '__main__':
    unittest.main()

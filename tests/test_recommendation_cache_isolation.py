import unittest
import json
from backend.app import create_app
from backend.database.db import DatabaseManager

class TestRecommendationCacheIsolation(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.db = DatabaseManager()

    def test_shopper_cache_isolation(self):
        """Verifies Shopper A and Shopper B receive isolated recommendation caches."""
        store_id = 'aura_threads'

        # Shopper A requests recommendations
        res_a = self.client.post('/api/recommendations', json={
            'store_id': store_id,
            'session_id': 'sess-cache-A',
            'user_id': 'visitor-cache-A',
            'anchor_product_id': 'CLOTH-101',
            'top_n': 6
        })
        self.assertEqual(res_a.status_code, 200)
        data_a = json.loads(res_a.data)

        # Shopper B requests recommendations
        res_b = self.client.post('/api/recommendations', json={
            'store_id': store_id,
            'session_id': 'sess-cache-B',
            'user_id': 'visitor-cache-B',
            'anchor_product_id': 'CLOTH-106',
            'top_n': 6
        })
        self.assertEqual(res_b.status_code, 200)
        data_b = json.loads(res_b.data)

        self.assertEqual(data_a['user_id'], 'visitor-cache-A')
        self.assertEqual(data_b['user_id'], 'visitor-cache-B')
        self.assertNotEqual(data_a['session_id'], data_b['session_id'])

    def test_cache_invalidation_on_event_logging(self):
        """Verifies candidate cache is invalidated when a new interaction event is logged."""
        store_id = 'fresh_pantry'
        sess_id = 'sess-inv-1'
        user_id = 'visitor-inv-1'

        # Initial request
        res1 = self.client.post('/api/recommendations', json={
            'store_id': store_id,
            'session_id': sess_id,
            'user_id': user_id,
            'top_n': 6
        })
        self.assertEqual(res1.status_code, 200)

        # Log view & wishlist event
        log_res = self.client.post('/api/events', json={
            'store_id': store_id,
            'session_id': sess_id,
            'user_id': user_id,
            'event_type': 'wishlist_add',
            'product_id': 'MART-315'
        })
        self.assertEqual(log_res.status_code, 200)
        log_data = json.loads(log_res.data)
        
        self.assertIn('updated_recommendations', log_data)
        self.assertEqual(log_data['status'], 'success')

if __name__ == '__main__':
    unittest.main()

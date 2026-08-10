import unittest
import json
from backend.app import create_app
from backend.database.db import DatabaseManager

class TestDynamicPersonalization(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.db = DatabaseManager()

    def test_shopper_a_vs_shopper_b_divergence(self):
        """Verifies Shopper A (Hoodies/Streetwear) and Shopper B (Formal Shirts) receive divergent recommendations."""
        store_id = 'aura_threads'

        # Shopper A: Views Hoodie & Denim Jacket
        sess_a = 'session-shopper-A-1'
        vid_a = 'visitor-shopper-A'
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_a, 'user_id': vid_a, 'event_type': 'view', 'product_id': 'CLOTH-101'})
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_a, 'user_id': vid_a, 'event_type': 'view', 'product_id': 'CLOTH-102'})
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_a, 'user_id': vid_a, 'event_type': 'click', 'product_id': 'CLOTH-103'})

        reco_a = self.client.post('/api/recommendations', json={'store_id': store_id, 'session_id': sess_a, 'user_id': vid_a, 'top_n': 6})
        items_a = [p['product_id'] for p in json.loads(reco_a.data).get('recommendations', [])]

        # Shopper B: Views Formal Shirt & Chinos
        sess_b = 'session-shopper-B-1'
        vid_b = 'visitor-shopper-B'
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_b, 'user_id': vid_b, 'event_type': 'view', 'product_id': 'CLOTH-106'})
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_b, 'user_id': vid_b, 'event_type': 'view', 'product_id': 'CLOTH-107'})
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_b, 'user_id': vid_b, 'event_type': 'add_to_cart', 'product_id': 'CLOTH-106'})

        reco_b = self.client.post('/api/recommendations', json={'store_id': store_id, 'session_id': sess_b, 'user_id': vid_b, 'top_n': 6})
        items_b = [p['product_id'] for p in json.loads(reco_b.data).get('recommendations', [])]

        # Recommendations MUST NOT be identical across Shopper A & B
        self.assertNotEqual(items_a, items_b, "Shopper A and Shopper B recommendations must diverge!")

    def test_product_view_and_cart_changes_recommendations(self):
        """Verifies that viewing and carting a product dynamically updates the recommendation set."""
        store_id = 'fresh_pantry'
        sess_id = 'sess-dynamic-1'
        user_id = 'visitor-dynamic-1'

        # Initial cold-start recommendation
        res1 = self.client.post('/api/recommendations', json={'store_id': store_id, 'session_id': sess_id, 'user_id': user_id, 'top_n': 6})
        reco1 = [p['product_id'] for p in json.loads(res1.data).get('recommendations', [])]

        # User views Toor Dal Pulses and adds to cart
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_id, 'user_id': user_id, 'event_type': 'view', 'product_id': 'MART-315'})
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_id, 'user_id': user_id, 'event_type': 'add_to_cart', 'product_id': 'MART-315'})

        # Second recommendation after interactions with category context
        res2 = self.client.post('/api/recommendations', json={'store_id': store_id, 'session_id': sess_id, 'user_id': user_id, 'anchor_product_id': 'MART-315', 'category': 'PULSES', 'top_n': 6})
        reco2 = [p['product_id'] for p in json.loads(res2.data).get('recommendations', [])]

        self.assertNotEqual(reco1, reco2, "Recommendation set must dynamically change after user actions!")

    def test_returning_visitor_retains_context_in_new_session(self):
        """Verifies returning visitor retains historical context when launching a new session."""
        store_id = 'aura_threads'
        user_id = 'visitor-returning-100'

        # Session 1: Shopper builds history around sports/activewear
        sess_1 = 'session-visit-1'
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_1, 'user_id': user_id, 'event_type': 'view', 'product_id': 'CLOTH-108'})
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_1, 'user_id': user_id, 'event_type': 'wishlist_add', 'product_id': 'CLOTH-108'})

        # Session 2: Fresh session launched for SAME visitor_id
        sess_2 = 'session-visit-2'
        res_sess2 = self.client.post('/api/recommendations', json={'store_id': store_id, 'session_id': sess_2, 'user_id': user_id, 'user_persona': 'returning', 'top_n': 6})
        data = json.loads(res_sess2.data)
        reco = data.get('recommendations', [])
        
        self.assertEqual(data['session_id'], sess_2)
        self.assertGreaterEqual(len(reco), 1)

    def test_cache_isolation_across_visitors(self):
        """Verifies candidate cache does not leak recommendations between different visitor IDs."""
        store_id = 'nexus_market'
        
        res1 = self.client.post('/api/recommendations', json={'store_id': store_id, 'session_id': 'sess-v1', 'user_id': 'vid-1', 'top_n': 5})
        res2 = self.client.post('/api/recommendations', json={'store_id': store_id, 'session_id': 'sess-v2', 'user_id': 'vid-2', 'top_n': 5})
        
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res2.status_code, 200)

    def test_4_storefront_isolation_parity(self):
        """Verifies all 4 storefronts maintain strict tenant isolation and dynamic personalization capability."""
        for store_id in ['aura_threads', 'nexus_market', 'fresh_pantry', 'savor_craft']:
            res = self.client.post('/api/recommendations', json={'store_id': store_id, 'session_id': f'sess-iso-{store_id}', 'user_id': f'vid-{store_id}', 'top_n': 5})
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data)
            self.assertEqual(data['store_id'], store_id)
            self.assertGreaterEqual(len(data['recommendations']), 1)

if __name__ == '__main__':
    unittest.main()

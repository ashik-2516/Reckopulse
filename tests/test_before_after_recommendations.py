import unittest
import json
from backend.app import create_app
from backend.database.db import DatabaseManager

class TestBeforeAfterRecommendations(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.db = DatabaseManager()

    def test_compare_endpoint_contract(self):
        """Verifies that /api/recommendations/compare returns valid comparison contract."""
        for store_id in ['aura_threads', 'nexus_market', 'fresh_pantry', 'savor_craft']:
            response = self.client.post('/api/recommendations/compare', json={
                'store_id': store_id,
                'session_id': 'test-session-cmp-1',
                'user_id': 'visitor-test-cmp-1',
                'top_n': 5
            })
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['store_id'], store_id)
            self.assertIn('without_recopulse', data)
            self.assertIn('with_recopulse', data)
            self.assertIn('metrics', data)
            self.assertIn('rank_displacements', data)
            
            # Baseline vs RecoPulse lists must be populated
            self.assertGreaterEqual(len(data['without_recopulse']), 1)
            self.assertGreaterEqual(len(data['with_recopulse']), 1)
            
            metrics = data['metrics']
            self.assertIn('top_1_changed', metrics)
            self.assertIn('top_5_overlap_score', metrics)
            self.assertIn('new_products_surfaced', metrics)
            self.assertIn('personalization_score', metrics)

    def test_rank_displacement_and_why_changed_explanations(self):
        """Verifies that rank displacements and signal explanations are present for every changed item."""
        response = self.client.post('/api/recommendations/compare', json={
            'store_id': 'aura_threads',
            'session_id': 'test-session-cmp-2',
            'user_id': 'visitor-test-cmp-2',
            'top_n': 6
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        displacements = data['rank_displacements']
        self.assertGreaterEqual(len(displacements), 1)

        for disp in displacements:
            self.assertIn('product_id', disp)
            self.assertIn('recopulse_rank', disp)
            self.assertIn('status', disp)
            self.assertIn('explanation', disp)

    def test_cart_recovery_and_merchant_analytics_integration(self):
        """Verifies cart recovery event logging and merchant analytics responsiveness."""
        store_id = 'aura_threads'
        sess_id = 'test-recovery-sess-99'
        user_id = 'visitor-recovery-99'

        # Log view, cart add, abandon, and recovery
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_id, 'user_id': user_id, 'event_type': 'view', 'product_id': 'CLOTH-101'})
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_id, 'user_id': user_id, 'event_type': 'add_to_cart', 'product_id': 'CLOTH-101'})
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_id, 'user_id': user_id, 'event_type': 'cart_abandoned', 'product_id': 'CLOTH-101'})
        self.client.post('/api/events', json={'store_id': store_id, 'session_id': sess_id, 'user_id': user_id, 'event_type': 'cart_recovered', 'product_id': 'CLOTH-101'})

        # Fetch analytics
        res = self.client.get(f'/api/analytics/{store_id}')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('retention', data)
        self.assertGreaterEqual(data['retention']['cart_recovered'], 1)

if __name__ == '__main__':
    unittest.main()

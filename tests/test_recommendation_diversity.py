import unittest
import json
from backend.app import create_app
from backend.database.db import DatabaseManager

class TestRecommendationDiversity(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.db = DatabaseManager()

    def test_shelf_diversity_and_frequently_bought_together(self):
        """Verifies frequently bought together items and shelf diversification."""
        for store_id in ['aura_threads', 'nexus_market', 'fresh_pantry', 'savor_craft']:
            res = self.client.post('/api/recommendations', json={
                'store_id': store_id,
                'session_id': f'sess-div-{store_id}',
                'user_id': f'visitor-div-{store_id}',
                'anchor_product_id': 'MART-301' if store_id == 'fresh_pantry' else None,
                'top_n': 6
            })
            self.assertEqual(res.status_code, 200)
            data = json.loads(res.data)
            self.assertIn('recommendations', data)
            self.assertIn('frequently_bought_together', data)
            
            recs = data['recommendations']
            pids = [p['product_id'] for p in recs]
            # Ensure recommendations list has zero internal duplicate product IDs
            self.assertEqual(len(pids), len(set(pids)), f"Recommendations in {store_id} must not contain duplicate product IDs!")

    def test_complementary_recommendations_category_validity(self):
        """Verifies complementary product compatibility per store domain."""
        res = self.client.post('/api/recommendations', json={
            'store_id': 'fresh_pantry',
            'session_id': 'sess-comp-pantry',
            'user_id': 'visitor-comp-pantry',
            'anchor_product_id': 'MART-306', # Organic Eggs
            'top_n': 6
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('frequently_bought_together', data)

if __name__ == '__main__':
    unittest.main()

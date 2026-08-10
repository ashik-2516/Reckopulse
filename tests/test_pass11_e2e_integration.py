import unittest
import json
import sqlite3
import tempfile
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app
from backend.database.db import DatabaseManager

class TestPass11E2EIntegration(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
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

    def test_full_shopper_journey_all_four_stores(self):
        stores = ['aura_threads', 'nexus_market', 'fresh_pantry', 'savor_craft']

        for store_id in stores:
            session_id = f"sess-e2e-{store_id}"

            # 1. Fetch catalog
            res_cat = self.app.get(f'/api/catalog/{store_id}')
            self.assertEqual(res_cat.status_code, 200)
            catalog = json.loads(res_cat.data)
            self.assertTrue(len(catalog) > 0)
            prod_id = catalog[0]['product_id']

            # 2. Get initial recommendations
            res_reco = self.app.post('/api/recommendations', json={
                'store_id': store_id,
                'session_id': session_id,
                'user_persona': 'new'
            })
            self.assertEqual(res_reco.status_code, 200)
            reco_data = json.loads(res_reco.data)
            self.assertEqual(reco_data['store_id'], store_id)

            # 3. Log click event
            res_click = self.app.post('/api/events', json={
                'store_id': store_id,
                'session_id': session_id,
                'event_type': 'click',
                'product_id': prod_id,
                'metadata': {'reason_type': 'collaborative'}
            })
            self.assertEqual(res_click.status_code, 200)

            # 4. Log purchase event
            res_purchase = self.app.post('/api/events', json={
                'store_id': store_id,
                'session_id': session_id,
                'event_type': 'purchase',
                'product_id': prod_id,
                'metadata': {'reason_type': 'collaborative'}
            })
            self.assertEqual(res_purchase.status_code, 200)

            # 5. Verify analytics increment
            res_analytics = self.app.get(f'/api/analytics/{store_id}')
            self.assertEqual(res_analytics.status_code, 200)
            analytics = json.loads(res_analytics.data)
            self.assertTrue(analytics['funnel']['total_events'] >= 2)

    def test_vendor_campaign_lifecycle_e2e(self):
        store_id = 'aura_threads'
        session_id = 'sess-vendor-campaign'

        # 1. Vendor activates trend on CLOTH-108
        res_trend = self.app.post('/api/merchant/trends', json={
            'store_id': store_id,
            'product_id': 'CLOTH-108',
            'trend_score': 4.5,
            'target_segments': ['active']
        })
        self.assertEqual(res_trend.status_code, 200)

        # 2. Immediately query recommendations on active user persona
        res_reco = self.app.post('/api/recommendations', json={
            'store_id': store_id,
            'session_id': session_id,
            'user_persona': 'active'
        })
        self.assertEqual(res_reco.status_code, 200)
        recos = json.loads(res_reco.data).get('recommendations', [])
        self.assertTrue(len(recos) > 0)
        top_pid = recos[0]['product_id']
        self.assertEqual(top_pid, 'CLOTH-108')

    def test_multi_store_multi_tenant_isolation(self):
        # 1. Activate trend rule on Aura Threads
        self.app.post('/api/merchant/trends', json={
            'store_id': 'aura_threads',
            'product_id': 'CLOTH-108',
            'trend_score': 4.5
        })

        # 2. Query FreshPantry recommendations
        res_fresh = self.app.post('/api/recommendations', json={
            'store_id': 'fresh_pantry',
            'session_id': 'sess-fresh-isolation',
            'user_persona': 'active'
        })
        self.assertEqual(res_fresh.status_code, 200)
        fresh_recos = json.loads(res_fresh.data).get('recommendations', [])
        
        # Verify no Aura products exist in FreshPantry recommendations
        fresh_pids = [r['product_id'] for r in fresh_recos]
        self.assertNotIn('CLOTH-108', fresh_pids)
        for pid in fresh_pids:
            self.assertTrue(pid.startswith('MART-'))


    def test_failure_recovery_and_unhappy_paths(self):
        # 1. Invalid store returns 404 contract
        res_bad_store = self.app.get('/api/catalog/invalid_store_domain')
        self.assertEqual(res_bad_store.status_code, 404)
        data_404 = json.loads(res_bad_store.data)
        self.assertEqual(data_404['code'], 'INVALID_STORE_ID')

        # 2. Missing product ID returns 400 contract
        res_bad_trend = self.app.post('/api/merchant/trends', json={'store_id': 'aura_threads'})
        self.assertEqual(res_bad_trend.status_code, 400)
        data_400 = json.loads(res_bad_trend.data)
        self.assertEqual(data_400['code'], 'MISSING_PRODUCT_ID')

if __name__ == '__main__':
    unittest.main()

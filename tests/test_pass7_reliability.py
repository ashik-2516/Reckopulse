import unittest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import app

class TestPass7Reliability(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_invalid_store_id_returns_404_json_contract(self):
        res = self.app.get('/api/catalog/non_existent_store')
        self.assertEqual(res.status_code, 404)
        data = json.loads(res.data)
        self.assertTrue(data.get('error'))
        self.assertEqual(data.get('code'), 'INVALID_STORE_ID')
        self.assertIn('timestamp', data)

    def test_malformed_top_n_parameter_returns_400(self):
        res = self.app.post('/api/recommendations', json={
            'store_id': 'aura_threads',
            'top_n': 'invalid_string'
        })
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertTrue(data.get('error'))
        self.assertEqual(data.get('code'), 'INVALID_PARAMETER')

    def test_missing_product_id_on_trend_returns_400(self):
        res = self.app.post('/api/merchant/trends', json={
            'store_id': 'aura_threads',
            'trend_score': 2.0
        })
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertTrue(data.get('error'))
        self.assertEqual(data.get('code'), 'MISSING_PRODUCT_ID')

    def test_cors_headers_present(self):
        res = self.app.get('/api/health')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Access-Control-Allow-Origin'), '*')
        self.assertIn('Content-Type', res.headers.get('Access-Control-Allow-Headers', ''))

if __name__ == '__main__':
    unittest.main()

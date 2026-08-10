import unittest
import json
import pandas as pd
from backend.app import app
from ml.pipeline.dataset_loader import DatasetLoader
from ml.pipeline.data_processor import DataProcessor
from ml.models.popularity import PopularityModel
from ml.models.content_based import ContentBasedModel
from ml.models.collaborative import CollaborativeFilteringModel
from ml.models.frequently_bought import FrequentlyBoughtTogetherModel
from ml.models.trend_engine import TrendEngine
from ml.models.lifecycle_churn import UserLifecycleChurnModel
from ml.ranking.hybrid_ranker import HybridRanker
from ml.evaluation.evaluator import ModelEvaluator

class TestRecommendationPlatform(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_dataset_loader_catalogs(self):
        loader = DatasetLoader()
        catalogs = loader.generate_domain_catalogs()
        self.assertIn('aura_threads', catalogs)
        self.assertIn('nexus_market', catalogs)
        self.assertIn('fresh_pantry', catalogs)
        self.assertIn('savor_craft', catalogs)
        self.assertGreaterEqual(len(catalogs['aura_threads']), 5)

    def test_trend_engine_precision_routing(self):
        trend = TrendEngine()
        trend.register_trend('t-101', 'CLOTH-104', trend_score=2.0, target_segments=['active'])
        
        # Match segment
        m1 = trend.get_trend_multiplier('CLOTH-104', user_segment='active')
        self.assertGreater(m1, 1.5)

        # Mismatched segment -> multiplier should be 1.0
        m2 = trend.get_trend_multiplier('CLOTH-104', user_segment='churn_risk')
        self.assertEqual(m2, 1.0)

    def test_user_lifecycle_churn_model(self):
        churn_model = UserLifecycleChurnModel()
        res_new = churn_model.evaluate_user_lifecycle('u-new', None)
        self.assertEqual(res_new['state'], 'new')

    def test_hybrid_ranker_output(self):
        loader = DatasetLoader()
        catalog = loader.get_catalog('aura_threads')
        ranker = HybridRanker()
        recs = ranker.rank(catalog_df=catalog, top_n=4)
        self.assertEqual(len(recs), 4)
        self.assertIn('final_score', recs[0])
        self.assertIn('score_breakdown', recs[0])

    def test_model_evaluator(self):
        evaluator = ModelEvaluator(k=3)
        actual = {'u1': ['p1', 'p2']}
        preds = {'u1': ['p1', 'p3', 'p4']}
        res = evaluator.evaluate_recommendations(actual, preds, ['p1', 'p2', 'p3', 'p4'])
        self.assertGreater(res['precision_at_k'], 0.0)
        self.assertGreater(res['recall_at_k'], 0.0)

    def test_api_health_check(self):
        res = self.app.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'healthy')

    def test_api_recommendations(self):
        res = self.app.post('/api/recommendations', json={
            'store_id': 'aura_threads',
            'session_id': 'test-session',
            'top_n': 5
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(len(data['recommendations']), 5)

    def test_api_events_ingestion(self):
        res = self.app.post('/api/events', json={
            'session_id': 'test-session',
            'store_id': 'aura_threads',
            'event_type': 'click',
            'product_id': 'CLOTH-101'
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'success')

    def test_api_analytics(self):
        res = self.app.get('/api/analytics/aura_threads')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('impressions', data)
        self.assertIn('ctr_percent', data)

if __name__ == '__main__':
    unittest.main()

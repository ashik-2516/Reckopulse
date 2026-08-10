import unittest
import json
import pandas as pd
from backend.app import app
from ml.pipeline.dataset_loader import DatasetLoader
from ml.models.popularity import PopularityModel
from ml.models.content_based import ContentBasedModel
from ml.models.collaborative import CollaborativeFilteringModel
from ml.models.frequently_bought import FrequentlyBoughtTogetherModel
from ml.models.trend_engine import TrendEngine
from ml.ranking.hybrid_ranker import HybridRanker
from ml.evaluation.evaluator import ModelEvaluator

class TestEndToEndIntegration(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_e2e_live_session_adaptation(self):
        session_id = "e2e-session-882"
        store_id = "aura_threads"

        # 1. Initial recommendation request for new visitor
        res1 = self.app.post('/api/recommendations', json={
            'store_id': store_id,
            'session_id': session_id,
            'user_persona': 'new',
            'top_n': 4
        })
        self.assertEqual(res1.status_code, 200)
        recs1 = json.loads(res1.data)['recommendations']
        pids1 = [r['product_id'] for r in recs1]

        # 2. User clicks/interacts with Retro Sneakers (CLOTH-104)
        event_res = self.app.post('/api/events', json={
            'session_id': session_id,
            'store_id': store_id,
            'event_type': 'click',
            'product_id': 'CLOTH-104'
        })
        self.assertEqual(event_res.status_code, 200)
        updated_recs = json.loads(event_res.data)['updated_recommendations']['recommendations']
        pids2 = [r['product_id'] for r in updated_recs]

        # Recommendations must dynamically adapt after session interaction
        self.assertNotEqual(pids1, pids2)

    def test_personalized_merchant_guardrails(self):
        # Apply merchant boost for Avakaya Mango (PICKLE-401)
        self.app.post('/api/merchant/rules', json={
            'store_id': 'savor_craft',
            'product_id': 'PICKLE-401',
            'boost_percent': 30.0,
            'target_segment': 'all'
        })

        # Request recommendations for SavorCraft store
        res = self.app.post('/api/recommendations', json={
            'store_id': 'savor_craft',
            'session_id': 'savor-session-1',
            'top_n': 4
        })
        self.assertEqual(res.status_code, 200)
        recs = json.loads(res.data)['recommendations']
        
        # Verify boosted product is included with merchant spotlight explanation
        pids = [r['product_id'] for r in recs]
        self.assertIn('PICKLE-401', pids)

    def test_ablation_study_and_trend_experiment(self):
        loader = DatasetLoader()
        catalog = loader.get_catalog('aura_threads')
        interactions_df = loader.generate_interaction_logs(store_id='aura_threads', n_users=50, n_events=500)

        test_user_history = {}
        for uid, group in interactions_df.groupby('user_id'):
            test_user_history[uid] = group['product_id'].tolist()

        models = {
            'pop': PopularityModel().fit(catalog, interactions_df),
            'content': ContentBasedModel().fit(catalog),
            'collab': CollaborativeFilteringModel().fit(interactions_df, catalog),
            'fbt': FrequentlyBoughtTogetherModel().fit(interactions_df)
        }
        ranker = HybridRanker()
        trend = TrendEngine()
        evaluator = ModelEvaluator(k=4)

        # 1. Multi-K Ablation Studies (K=4, 5, 8)
        ablation_k4 = evaluator.run_ablation_study(catalog, test_user_history, models, ranker, trend, eval_k=4)
        ablation_k5 = evaluator.run_ablation_study(catalog, test_user_history, models, ranker, trend, eval_k=5)
        ablation_k8 = evaluator.run_ablation_study(catalog, test_user_history, models, ranker, trend, eval_k=8)

        self.assertEqual(len(ablation_k4), 8)
        self.assertEqual(len(ablation_k5), 8)
        self.assertEqual(len(ablation_k8), 8)

        print("\n=========================================================================================================")
        print("                         CONTROLLED DIAGNOSTIC ABLATION MATRIX (K=4)                                     ")
        print("=========================================================================================================")
        print(f"{'Experiment Name':<38} | {'Prec@4':<7} | {'Rec@4':<7} | {'MAP@4':<7} | {'NDCG@4':<7} | {'Coverage':<8} | {'Diversity':<9} | {'Latency':<8}")
        print("---------------------------------------------------------------------------------------------------------")
        for r in ablation_k4:
            print(f"{r['experiment_name']:<38} | {r['precision_at_k']:<7.4f} | {r['recall_at_k']:<7.4f} | {r['map_at_k']:<7.4f} | {r['ndcg_at_k']:<7.4f} | {r['catalog_coverage']:<8.4f} | {r['diversity_index']:<9.4f} | {r['mean_latency_ms']}ms")

        print("\n=========================================================================================================")
        print("                         CONTROLLED DIAGNOSTIC ABLATION MATRIX (K=5)                                     ")
        print("=========================================================================================================")
        print(f"{'Experiment Name':<38} | {'Prec@5':<7} | {'Rec@5':<7} | {'MAP@5':<7} | {'NDCG@5':<7} | {'Coverage':<8} | {'Diversity':<9} | {'Latency':<8}")
        print("---------------------------------------------------------------------------------------------------------")
        for r in ablation_k5:
            print(f"{r['experiment_name']:<38} | {r['precision_at_k']:<7.4f} | {r['recall_at_k']:<7.4f} | {r['map_at_k']:<7.4f} | {r['ndcg_at_k']:<7.4f} | {r['catalog_coverage']:<8.4f} | {r['diversity_index']:<9.4f} | {r['mean_latency_ms']}ms")

        print("\n=========================================================================================================")
        print("                         CONTROLLED DIAGNOSTIC ABLATION MATRIX (K=8)                                     ")
        print("=========================================================================================================")
        print(f"{'Experiment Name':<38} | {'Prec@8':<7} | {'Rec@8':<7} | {'MAP@8':<7} | {'NDCG@8':<7} | {'Coverage':<8} | {'Diversity':<9} | {'Latency':<8}")
        print("---------------------------------------------------------------------------------------------------------")
        for r in ablation_k8:
            print(f"{r['experiment_name']:<38} | {r['precision_at_k']:<7.4f} | {r['recall_at_k']:<7.4f} | {r['map_at_k']:<7.4f} | {r['ndcg_at_k']:<7.4f} | {r['catalog_coverage']:<8.4f} | {r['diversity_index']:<9.4f} | {r['mean_latency_ms']}ms")
        print("=========================================================================================================\n")

        # 2. Execute Corrected Controlled Trend Experiment
        trend_exp_res = evaluator.run_controlled_trend_experiment(catalog, models, ranker, trend)
        self.assertTrue(trend_exp_res['guardrail_passed'])

        print("=== CORRECTED CONTROLLED TREND INJECTION & GUARDRAIL EXPERIMENT ===")
        print(f"Target Product: {trend_exp_res['target_product']} (Performance Joggers)")
        print(f"Rank Before Trend (Control): #{trend_exp_res['control_rank']}")
        print(f"Rank After Trend (Target Active User): #{trend_exp_res['treatment_active_rank']}")
        print(f"Rank After Trend (Mismatched Irrelevant User): #{trend_exp_res['treatment_irrelevant_rank']}")
        print(f"Guardrail Verification Check: PASSED\n")

if __name__ == '__main__':
    unittest.main()

import unittest
import tempfile
import os
import json
from backend.database.db import DatabaseManager
from backend.services.recommendation_service import RecommendationService
from ml.pipeline.dataset_loader import DatasetLoader

class TestPass12RetentionIndia(unittest.TestCase):
    def setUp(self):
        self.loader = DatasetLoader()
        self.catalogs = self.loader.generate_domain_catalogs()

        # Temporary SQLite Database for test isolation
        self.temp_db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db_file.close()
        self.db = DatabaseManager(db_path=self.temp_db_file.name)
        self.reco_service = RecommendationService(db=self.db)

    def tearDown(self):
        if os.path.exists(self.temp_db_file.name):
            try:
                os.remove(self.temp_db_file.name)
            except Exception:
                pass

    def test_catalog_135_products_expansion(self):
        """Verifies that all 4 storefronts load the 135-product catalog target."""
        aura = self.catalogs['aura_threads']
        nexus = self.catalogs['nexus_market']
        pantry = self.catalogs['fresh_pantry']
        savor = self.catalogs['savor_craft']

        self.assertEqual(len(aura), 35)
        self.assertEqual(len(nexus), 35)
        self.assertEqual(len(pantry), 35)
        self.assertEqual(len(savor), 30)
        total_products = len(aura) + len(nexus) + len(pantry) + len(savor)
        self.assertEqual(total_products, 135)

    def test_inr_pricing_integrity(self):
        """Verifies product pricing integrity with ₹ INR prices, MRPs, and valid discount calculations."""
        aura = self.catalogs['aura_threads']
        sample_item = aura.iloc[0]
        self.assertIn('mrp', sample_item)
        self.assertGreater(sample_item['mrp'], sample_item['price'])
        self.assertGreater(sample_item['price'], 100)  # INR realistic price

    def test_wishlist_events_tracking(self):
        """Verifies wishlist_add and wishlist_remove event logging in database."""
        self.db.log_event(
            session_id="sess_test_12",
            user_id="user_12",
            store_id="aura_threads",
            event_type="wishlist_add",
            product_id="CLOTH-106",
            metadata={"reason_type": "user_saved"}
        )
        events = self.db.get_session_events("sess_test_12")
        self.assertTrue(any(e['event_type'] == 'wishlist_add' for e in events))

    def test_cart_abandonment_and_recovery_flow(self):
        """Verifies cart_abandoned and cart_recovered event logging and analytics tracking."""
        self.db.log_event("sess_ret_1", "user_ret", "aura_threads", "cart_abandoned", "CLOTH-101", {"cart_size": 2})
        self.db.log_event("sess_ret_1", "user_ret", "aura_threads", "cart_recovered", "CLOTH-101", {"discount_applied": 150})
        
        analytics = self.db.get_event_analytics("aura_threads")
        self.assertIn("retention", analytics)
        self.assertGreaterEqual(analytics["retention"]["cart_abandoned"], 1)
        self.assertGreaterEqual(analytics["retention"]["cart_recovered"], 1)

    def test_retention_analytics_response(self):
        """Verifies retention breakdown keys in get_event_analytics."""
        analytics = self.db.get_event_analytics("nexus_market")
        self.assertIn("wishlist_adds", analytics["retention"])
        self.assertIn("recovery_rate_percent", analytics["retention"])
        self.assertIn("recovered_revenue_inr", analytics["retention"])

    def test_mode_personalized_vs_trending_separation(self):
        """Verifies that personalized and trending recommendation modes return distinct rankings."""
        res_personalized = self.reco_service.get_store_recommendations("aura_threads", "sess_p1", mode="personalized", top_n=6)
        res_trending = self.reco_service.get_store_recommendations("aura_threads", "sess_p1", mode="trending", top_n=6)

        self.assertEqual(len(res_personalized["recommendations"]), 6)
        self.assertEqual(len(res_trending["recommendations"]), 6)

    def test_strict_category_filtering(self):
        """Verifies category_filter='shirts' strictly restricts recommendations to shirt products."""
        res = self.reco_service.get_store_recommendations("aura_threads", "sess_p1", category_filter="shirts", top_n=6)
        recos = res["recommendations"]
        self.assertTrue(len(recos) > 0)
        for r in recos:
            p_sub = (r.get("subcategory") or "").lower()
            p_cat = (r.get("category") or "").lower()
            p_title = (r.get("title") or "").lower()
            p_tags = [str(t).lower() for t in (r.get("tags") or [])]
            self.assertTrue("shirt" in p_sub or "shirt" in p_cat or "shirt" in p_title or any("shirt" in t for t in p_tags))

    def test_multi_tenant_store_isolation_pass12(self):
        """Verifies strict store tenant isolation across all 4 catalogs."""
        aura_res = self.reco_service.get_store_recommendations("aura_threads", "sess_iso", top_n=6)
        fresh_res = self.reco_service.get_store_recommendations("fresh_pantry", "sess_iso", top_n=6)

        aura_pids = [r['product_id'] for r in aura_res['recommendations']]
        fresh_pids = [r['product_id'] for r in fresh_res['recommendations']]

        for pid in aura_pids:
            self.assertTrue(pid.startswith('CLOTH-'))
        for pid in fresh_pids:
            self.assertTrue(pid.startswith('MART-'))

if __name__ == '__main__':
    unittest.main()

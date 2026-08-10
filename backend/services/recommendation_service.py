import time
import pandas as pd
from ml.pipeline.dataset_loader import DatasetLoader
from ml.models.popularity import PopularityModel
from ml.models.content_based import ContentBasedModel
from ml.models.collaborative import CollaborativeFilteringModel
from ml.models.frequently_bought import FrequentlyBoughtTogetherModel
from ml.models.trend_engine import TrendEngine
from ml.models.lifecycle_churn import UserLifecycleChurnModel
from ml.ranking.hybrid_ranker import HybridRanker
from backend.database.db import DatabaseManager

class RecommendationService:
    """
    Central Orchestrator for Multi-Store Recommendation API.
    Manages model instances per store, candidate-level context-aware caching,
    cross-worker cache invalidation broadcasting with graceful fallback,
    targeted trend injection, merchant rules, and user persona simulations.
    """

    def __init__(self, db_manager=None, invalidation_bus=None, db=None):
        self.db = db or db_manager or DatabaseManager()
        self.loader = DatasetLoader()

        self.catalogs = self.loader.generate_domain_catalogs()
        self.invalidation_bus = invalidation_bus
        
        # Per-store ML models
        self.models = {}
        self.trend_engines = {}
        self.ranker = HybridRanker()
        self.lifecycle_model = UserLifecycleChurnModel()

        # Context-Aware Candidate Caching System
        self.candidate_cache = {}
        self.cache_version = 1

        self._initialize_store_models()
        self._subscribe_invalidation_bus()

    def _initialize_store_models(self):
        """Initializes and fits ML sub-models for each store catalog."""
        for store_id, catalog_df in self.catalogs.items():
            interactions_df = self.loader.generate_interaction_logs(store_id=store_id, n_users=50, n_events=500)

            pop = PopularityModel().fit(catalog_df, interactions_df)
            content = ContentBasedModel().fit(catalog_df)
            collab = CollaborativeFilteringModel().fit(interactions_df, catalog_df)
            fbt = FrequentlyBoughtTogetherModel().fit(interactions_df)

            trend = TrendEngine()
            
            self.models[store_id] = {
                'pop': pop,
                'content': content,
                'collab': collab,
                'fbt': fbt,
                'interactions': interactions_df
            }
            self.trend_engines[store_id] = trend

    def _subscribe_invalidation_bus(self):
        """Subscribes to shared invalidation bus with fallback protection."""
        if self.invalidation_bus:
            try:
                self.invalidation_bus.subscribe('CACHE_INVALIDATE', self._on_remote_invalidation)
            except Exception as err:
                print(f"[RecommendationService] Invalidation bus subscription failed ({err}). Operating in local TTL mode.")

    def _on_remote_invalidation(self, message):
        """Handles incoming cross-worker cache invalidation messages."""
        self.cache_version += 1
        self.candidate_cache.clear()

    def invalidate_cache(self, broadcast=True):
        """Invalidates local candidate cache and broadcasts invalidation signal if enabled."""
        self.cache_version += 1
        self.candidate_cache.clear()
        
        if broadcast and self.invalidation_bus:
            try:
                self.invalidation_bus.publish('CACHE_INVALIDATE', {'version': self.cache_version, 'timestamp': time.time()})
            except Exception as err:
                print(f"[RecommendationService] Warning: Invalidation bus publish failed ({err}). Operating on local TTL.")

    def get_store_recommendations(
        self,
        store_id,
        session_id,
        user_id=None,
        user_persona='new',
        anchor_product_id=None,
        category_filter=None,
        mode='personalized',
        top_n=6
    ):
        """
        Generates contextual hybrid recommendations with candidate caching & causally accurate metadata.
        """
        catalog_df = self.catalogs.get(store_id, self.catalogs['aura_threads'])
        models = self.models.get(store_id, self.models['aura_threads'])
        trend_eng = self.trend_engines.get(store_id, self.trend_engines['aura_threads'])

        # Load live session events and returning visitor history from DB
        session_events = self.db.get_session_events(session_id, user_id=user_id)
        merchant_rules = self.db.get_merchant_rules(store_id)
        db_trends = self.db.get_trends(store_id)

        # Synthesize persona-specific context signals when evaluator persona is selected
        effective_user_id = user_id
        if user_persona == 'returning':
            effective_user_id = user_id if (user_id and user_id != 'visitor_demo') else 'user_1'
        elif user_persona == 'active' and not session_events:
            # Default active interest product per store
            store_anchors = {
                'aura_threads': 'CLOTH-106',
                'nexus_marketplace': 'NEX-202',
                'fresh_pantry': 'MART-306',
                'savor_craft': 'PICKLE-401'
            }
            session_events = [{'event_type': 'view', 'product_id': store_anchors.get(store_id, 'CLOTH-106')}]

        # Infer anchor_product_id from recent session events if not explicitly passed
        if not anchor_product_id and session_events:
            for ev in session_events:
                if ev.get('product_id'):
                    anchor_product_id = ev['product_id']
                    break

        # Contextual Candidate Cache Keying (isolates per store, session, visitor, persona, anchor, category, mode, top_n, cache_version)
        cache_key = (store_id, session_id, effective_user_id, user_persona, anchor_product_id, category_filter, mode, top_n, self.cache_version)
        if cache_key in self.candidate_cache:
            return self.candidate_cache[cache_key]

        # Sync DB active trends to trend engine
        for tr in db_trends:
            trend_eng.register_trend(
                trend_id=tr['trend_id'],
                product_id=tr['product_id'],
                trend_score=tr['trend_score'],
                target_segments=tr.get('target_segments'),
                source_url=tr.get('source_url'),
                duration_hours=tr.get('duration_hours', 48)
            )

        # Synthesize user lifecycle profile from persona or events
        if user_persona == 'churn_risk':
            user_lifecycle = {'state': 'churn_risk', 'churn_risk_score': 0.85, 'strategy': 'winback_preferred_categories'}
        elif user_persona == 'returning':
            user_lifecycle = {'state': 'returning', 'churn_risk_score': 0.35, 'strategy': 'recent_session_plus_longterm'}
        elif user_persona == 'active' or len(session_events) >= 1:
            user_lifecycle = {'state': 'active', 'churn_risk_score': 0.10, 'strategy': 'personalized_hybrid'}
        else:
            user_lifecycle = {'state': 'new', 'churn_risk_score': 0.0, 'strategy': 'cold_start_popularity_trends'}

        # Execute Hybrid Ranker
        ranked_products = self.ranker.rank(
            catalog_df=catalog_df,
            pop_model=models['pop'],
            content_model=models['content'],
            collab_model=models['collab'],
            fbt_model=models['fbt'],
            trend_engine=trend_eng,
            merchant_rules=merchant_rules,
            session_events=session_events,
            user_lifecycle=user_lifecycle,
            anchor_product_id=anchor_product_id,
            user_id=effective_user_id,
            category_filter=category_filter,
            top_n=top_n
        )

        if mode == 'trending':
            # For trending mode, prioritize products with trend/merchant signals or top rating velocity
            trending_products = sorted(
                ranked_products,
                key=lambda p: (
                    p.get('explanation_metadata', {}).get('reason_type') == 'trend',
                    p.get('explanation_metadata', {}).get('reason_type') == 'merchant',
                    p.get('rating', 0),
                    p.get('price', 0)
                ),
                reverse=True
            )
            for idx, prod in enumerate(trending_products):
                prod['rank'] = idx + 1
            ranked_products = trending_products

        # Get complementary "Frequently Bought Together" items if anchor product is given or from latest event
        effective_anchor = anchor_product_id
        if not effective_anchor and session_events:
            for ev in session_events:
                if ev.get('product_id'):
                    effective_anchor = ev['product_id']
                    break

        fbt_items = []
        if effective_anchor:
            fbt_items = models['fbt'].get_frequently_bought(effective_anchor, catalog_df, top_n=3)

        result_payload = {
            "store_id": store_id,
            "session_id": session_id,
            "user_id": user_id,
            "user_persona": user_persona,
            "user_lifecycle": user_lifecycle,
            "anchor_product_id": anchor_product_id,
            "category_filter": category_filter,
            "recommendations": ranked_products,
            "frequently_bought_together": fbt_items
        }

        self.candidate_cache[cache_key] = result_payload
        return result_payload

    def get_baseline_recommendations(self, store_id, category_filter=None, top_n=6):
        """
        Generates non-personalized baseline recommendations (WITHOUT RecoPulse).
        Uses pure popularity / default catalog ordering with zero session signals, zero SVD, zero TF-IDF, zero trend, zero merchant rules.
        """
        catalog_df = self.catalogs.get(store_id, self.catalogs['aura_threads']).copy()
        models = self.models.get(store_id, self.models['aura_threads'])

        # Simple popularity / default ranking
        pop_model = models['pop']
        pop_scores = [pop_model.global_scores.get(row['product_id'], float(row.get('rating', 4.0))) for _, row in catalog_df.iterrows()]
        catalog_df['pop_score'] = pop_scores

        if category_filter and category_filter != 'all':
            cat_lower = str(category_filter).strip().lower()
            catalog_df = catalog_df[catalog_df['category'].str.strip().str.lower() == cat_lower]

        sorted_df = catalog_df.sort_values(by=['pop_score', 'rating', 'price'], ascending=[False, False, True]).head(top_n)

        baseline_list = []
        for idx, row in enumerate(sorted_df.to_dict('records')):
            item = dict(row)
            item['rank'] = idx + 1
            item['explanation'] = "Storewide Popular Item (Default Baseline — No RecoPulse)"
            item['explanation_metadata'] = {
                "reason_type": "popularity",
                "explanation": "Storewide Popular Item (Default Baseline — No RecoPulse)",
                "signal_attribution": {"popularity": 1.0}
            }
            baseline_list.append(item)

        return baseline_list

    def compare_recommendations(
        self,
        store_id,
        session_id=None,
        user_id=None,
        user_persona='new',
        anchor_product_id=None,
        category_filter=None,
        top_n=6
    ):
        """
        Executes a controlled side-by-side empirical comparison:
        WITHOUT RECO PULSE (Baseline Popularity) vs WITH RECO PULSE (Hybrid Personalized Engine)
        under identical shopper, store, catalog, and timestamp conditions.
        """
        session_id = session_id or 'comparison-session-1'
        baseline = self.get_baseline_recommendations(store_id, category_filter=category_filter, top_n=top_n)
        recopulse_res = self.get_store_recommendations(
            store_id=store_id,
            session_id=session_id,
            user_id=user_id,
            user_persona=user_persona,
            anchor_product_id=anchor_product_id,
            category_filter=category_filter,
            top_n=top_n
        )

        recopulse = recopulse_res.get('recommendations', [])
        for idx, item in enumerate(recopulse):
            if 'rank' not in item:
                item['rank'] = idx + 1

        for idx, item in enumerate(baseline):
            if 'rank' not in item:
                item['rank'] = idx + 1

        # Calculate empirical rank movement metrics
        baseline_map = {item['product_id']: item['rank'] for item in baseline}
        recopulse_map = {item['product_id']: item['rank'] for item in recopulse}

        displacements = []
        for r_item in recopulse:
            pid = r_item['product_id']
            r_rank = r_item['rank']
            if pid in baseline_map:
                b_rank = baseline_map[pid]
                delta = b_rank - r_rank  # positive means moved UP in ranking
                status = f"↑ {delta}" if delta > 0 else (f"↓ {abs(delta)}" if delta < 0 else "—")
            else:
                delta = None
                status = "NEW"

            displacements.append({
                "product_id": pid,
                "title": r_item['title'],
                "price": r_item['price'],
                "recopulse_rank": r_rank,
                "baseline_rank": baseline_map.get(pid),
                "delta": delta,
                "status": status,
                "explanation": r_item.get('explanation', 'Personalized hybrid signal')
            })

        b_top1 = baseline[0]['product_id'] if baseline else None
        r_top1 = recopulse[0]['product_id'] if recopulse else None
        top_1_changed = (b_top1 != r_top1) if (b_top1 and r_top1) else False

        b_top5_set = set(item['product_id'] for item in baseline[:5])
        r_top5_set = set(item['product_id'] for item in recopulse[:5])

        overlap_count = len(b_top5_set & r_top5_set)
        max_possible = max(1, min(5, len(b_top5_set)))
        overlap_score = round(overlap_count / max_possible, 2)

        new_surfaced_count = sum(1 for d in displacements if d['status'] == 'NEW')
        personalization_score = round(1.0 - overlap_score, 2)

        return {
            "store_id": store_id,
            "session_id": session_id,
            "user_id": user_id,
            "anchor_product_id": anchor_product_id,
            "category_filter": category_filter,
            "comparison_label": "Controlled Baseline vs RecoPulse Intelligence",
            "metrics": {
                "top_1_changed": top_1_changed,
                "baseline_top1_id": b_top1,
                "recopulse_top1_id": r_top1,
                "top_5_overlap_count": overlap_count,
                "top_5_overlap_score": overlap_score,
                "new_products_surfaced": new_surfaced_count,
                "personalization_score": personalization_score
            },
            "without_recopulse": baseline,
            "with_recopulse": recopulse,
            "rank_displacements": displacements,
            "frequently_bought_together": recopulse_res.get('frequently_bought_together', [])
        }

import pandas as pd
import numpy as np

class HybridRanker:
    """
    Evidence-Driven Hybrid Ranker with Task-Aware Weighting,
    Personalized Merchant Guardrails, Causally Accurate Explanation Metadata,
    and MMR Subcategory Diversity.
    Optimized in Pass #3 for zero redundant candidate scoring lookups.
    """

    def __init__(self, lambda_diversity=0.7):
        self.lambda_diversity = lambda_diversity

    def rank(
        self,
        catalog_df,
        pop_model=None,
        content_model=None,
        collab_model=None,
        fbt_model=None,
        trend_engine=None,
        merchant_rules=None,
        session_events=None,
        user_lifecycle=None,
        anchor_product_id=None,
        user_id=None,
        category_filter=None,
        top_n=4,
        exclude_ids=None,
        candidate_pool_size=50,
        enable_mmr=True
    ):
        """
        Executes single-pass candidate retrieval, evidence-driven hybrid scoring, causally accurate explanation metadata, and MMR diversity.
        """
        if exclude_ids is None:
            exclude_ids = set()

        if anchor_product_id:
            exclude_ids.add(anchor_product_id)

        catalog = catalog_df.copy()
        if category_filter and category_filter.lower() != 'all':
            filtered_cat = catalog[catalog['category'].str.lower() == category_filter.lower()]
            if not filtered_cat.empty:
                catalog = filtered_cat

        # STAGE 1: Candidate Retrieval Pool & Single-Pass Pre-Scoring
        candidates = {}

        def get_or_create(pid):
            if pid not in candidates:
                row = catalog[catalog['product_id'] == pid]
                if not row.empty:
                    candidates[pid] = {
                        'product': row.iloc[0].to_dict(),
                        'collab_score': 0.0,
                        'content_score': 0.0,
                        'pop_score': 0.0,
                        'session_score': 0.0,
                        'trend_multiplier': 1.0,
                        'merchant_boost': 0.0
                    }
            return candidates.get(pid)
        
        # Source 1: Collaborative Filtering SVD
        if collab_model:
            if user_id:
                collab_recs = collab_model.recommend_for_user(user_id, catalog, top_n=candidate_pool_size)
            elif anchor_product_id:
                collab_recs = collab_model.get_collaborative_similar(anchor_product_id, catalog, top_n=candidate_pool_size)
            else:
                collab_recs = []
            max_collab = max([r.get('collab_score', 0.0) for r in collab_recs], default=1.0) or 1.0
            for r in collab_recs:
                pid = r['product_id']
                if pid not in exclude_ids:
                    c = get_or_create(pid)
                    if c:
                        c['collab_score'] = float(r.get('collab_score', 0.0)) / max_collab

        # Source 2: Content-Based TF-IDF
        if content_model and anchor_product_id:
            content_recs = content_model.get_similar_products(anchor_product_id, top_n=candidate_pool_size)
            max_content = max([r.get('content_score', 0.0) for r in content_recs], default=1.0) or 1.0
            for r in content_recs:
                pid = r['product_id']
                if pid not in exclude_ids:
                    c = get_or_create(pid)
                    if c:
                        c['content_score'] = float(r.get('content_score', 0.0)) / max_content

        # Source 3: Popularity & Velocity
        if pop_model:
            pop_recs = pop_model.recommend(catalog, category=category_filter, top_n=candidate_pool_size)
            max_pop = max([r['pop_score'] for r in pop_recs], default=1.0) or 1.0
            for r in pop_recs:
                pid = r['product_id']
                if pid not in exclude_ids:
                    c = get_or_create(pid)
                    if c:
                        c['pop_score'] = float(r['pop_score']) / max_pop

        # Fallback: Catalog items if pool is small
        if len(candidates) < top_n:
            for pid in catalog['product_id'].values:
                if pid not in exclude_ids:
                    get_or_create(pid)

        session_pids = [e['product_id'] for e in (session_events or []) if 'product_id' in e]
        user_segment = user_lifecycle.get('state', 'new') if user_lifecycle else 'new'

        # Source 4: Session Intent
        if session_pids and content_model:
            latest_pid = session_pids[-1]
            session_recs = content_model.get_similar_products(latest_pid, top_n=len(candidates))
            max_sess = max([r.get('content_score', 0.0) for r in session_recs], default=1.0) or 1.0
            for r in session_recs:
                pid = r['product_id']
                if pid in candidates:
                    candidates[pid]['session_score'] = float(r.get('content_score', 0.0)) / max_sess

        # Source 5: Trend Engine Signals
        if trend_engine:
            for pid, cand in candidates.items():
                p_cat = cand['product'].get('category')
                mult = trend_engine.get_trend_multiplier(
                    product_id=pid,
                    user_segment=user_segment,
                    product_category=p_cat
                )
                cand['trend_multiplier'] = mult

        # Source 6: Merchant Rules Guardrails
        if merchant_rules:
            for rule in merchant_rules:
                r_pid = rule.get('product_id')
                boost = float(rule.get('boost_percent', 0)) / 100.0
                seg = rule.get('target_segment', 'all')
                
                if (r_pid in candidates) and (seg == 'all' or seg == user_segment):
                    candidates[r_pid]['merchant_boost'] += boost

        # STAGE 1.5: Strict Category Constraint Filtering
        if category_filter and category_filter != 'all':
            cat_query = str(category_filter).lower().strip()
            cat_matched_candidates = {}
            for pid, cand in candidates.items():
                p = cand['product']
                p_cat = (p.get('category') or '').lower()
                p_sub = (p.get('subcategory') or '').lower()
                p_title = (p.get('title') or '').lower()
                p_tags = [str(t).lower() for t in (p.get('tags') or [])]
                
                if cat_query in p_cat or cat_query in p_sub or cat_query in p_title or any(cat_query in t for t in p_tags):
                    cat_matched_candidates[pid] = cand

            if cat_matched_candidates:
                candidates = cat_matched_candidates

            # STAGE 2: Persona-Driven Dynamic Weight Allocation & Explanation Packaging
        scored_pool = []
        for pid, cand in candidates.items():
            has_collab = cand['collab_score'] > 0.0
            has_content = cand['content_score'] > 0.0
            has_session = cand['session_score'] > 0.0
            has_trend = cand['trend_multiplier'] > 1.1
            has_merchant = cand['merchant_boost'] > 0.0

            if user_segment == 'churn_risk':
                # Win-Back Retargeting: Heavy boost on high-discount (25%+ OFF) & high-value items
                w_collab, w_content, w_pop, w_sess = 0.20, 0.10, 0.50, 0.20
                mrp = float(cand['product'].get('mrp') or cand['product'].get('price', 1) * 1.25)
                price = float(cand['product'].get('price', 1))
                disc_ratio = max(0.0, (mrp - price) / mrp)
                persona_multiplier = 1.0 + (disc_ratio * 3.0)

            elif user_segment == 'returning':
                # Long-Term Member: Collaborative SVD & Long-Term Style Matching
                if has_collab:
                    w_collab, w_content, w_pop, w_sess = 0.85, 0.10, 0.00, 0.05
                    persona_multiplier = 1.0 + (cand['collab_score'] * 2.0)
                else:
                    w_collab, w_content, w_pop, w_sess = 0.00, 0.60, 0.20, 0.20
                    persona_multiplier = 1.0

            elif user_segment == 'active':
                # Active Shopper: Active Session Interest & Content Preference
                if has_content or has_session:
                    w_collab, w_content, w_pop, w_sess = 0.10, 0.55, 0.05, 0.30
                    persona_multiplier = 1.0 + (cand['content_score'] * 1.8) + (cand['session_score'] * 1.8)
                else:
                    w_collab, w_content, w_pop, w_sess = 0.00, 0.20, 0.50, 0.30
                    persona_multiplier = 1.0

            else:
                # New Visitor Cold-Start: Popularity & Store Rating Velocity
                w_collab, w_content, w_pop, w_sess = 0.00, 0.05, 0.85, 0.10
                persona_multiplier = 1.0 + (cand['pop_score'] * 1.2)

            calc_organic = (
                w_collab * cand['collab_score'] +
                w_content * cand['content_score'] +
                w_pop * cand['pop_score'] +
                w_sess * cand['session_score']
            )

            base_rating_score = float(cand['product'].get('rating', 4.0)) / 5.0
            organic_score = max(calc_organic, 0.20 * base_rating_score) * persona_multiplier
            score_with_trend = organic_score * cand['trend_multiplier']

            if has_merchant:
                final_score = score_with_trend * (1.0 + cand['merchant_boost'] * organic_score)
            else:
                final_score = score_with_trend

            contributing_signals = []
            if has_collab: contributing_signals.append('collaborative')
            if has_content: contributing_signals.append('content')
            if has_session: contributing_signals.append('session')
            if has_trend: contributing_signals.append('trend')
            if has_merchant: contributing_signals.append('merchant')
            if cand['pop_score'] > 0.0: contributing_signals.append('popularity')

            p_cat = cand['product'].get('category', 'Category')
            if has_merchant:
                reason_type = 'merchant'
                reason_source = 'merchant_rule'
                explanation = f"⭐ Merchant Featured ({int(cand['merchant_boost']*100)}% Boost)"
            elif has_trend:
                reason_type = 'trend'
                reason_source = 'trend_engine'
                explanation = f"Trending in {p_cat}"
            elif user_segment == 'churn_risk':
                reason_type = 'churn_risk'
                reason_source = 'winback_engine'
                explanation = "Win-Back Special Retention Offer"
            elif user_segment == 'returning' and has_collab:
                reason_type = 'collaborative'
                reason_source = 'svd'
                explanation = "⭐ Based on your long-term shopping style"
            elif user_segment == 'active' and (has_content or has_session):
                reason_type = 'content'
                reason_source = 'session_history'
                explanation = "Similar to your recent active views"
            elif has_collab:
                reason_type = 'collaborative'
                reason_source = 'svd'
                explanation = "Based on your shopping preferences"
            elif has_session:
                reason_type = 'session'
                reason_source = 'session_history'
                explanation = "Matches your active session interest"
            elif has_content:
                reason_type = 'content'
                reason_source = 'tfidf'
                explanation = "Similar style to viewed item"
            else:
                reason_type = 'popularity'
                reason_source = 'popularity'
                explanation = "Popular customer pick"

            res_obj = cand['product'].copy()
            res_obj['final_score'] = round(float(final_score), 4)
            res_obj['score_breakdown'] = {
                'organic_score': round(float(organic_score), 3),
                'collab': round(float(cand['collab_score']), 3),
                'content': round(float(cand['content_score']), 3),
                'popularity': round(float(cand['pop_score']), 3),
                'session': round(float(cand['session_score']), 3),
                'trend_multiplier': round(float(cand['trend_multiplier']), 2),
                'merchant_boost': round(float(cand['merchant_boost']), 2)
            }
            res_obj['explanation'] = explanation
            res_obj['explanation_metadata'] = {
                'reason_type': reason_type,
                'reason_source': reason_source,
                'reason_context': user_segment,
                'explanation': explanation,
                'contributing_signals': contributing_signals
            }
            scored_pool.append(res_obj)

        scored_pool.sort(key=lambda x: x['final_score'], reverse=True)

        if not enable_mmr:
            return scored_pool[:top_n]

        # STAGE 3: Maximal Marginal Relevance (MMR) Diversity Filter
        selected_results = []
        selected_subcategories = {}

        for item in scored_pool:
            subcat = item.get('subcategory', item.get('category', 'General'))
            count = selected_subcategories.get(subcat, 0)

            if count >= 2 and len(scored_pool) >= top_n * 2:
                continue

            selected_results.append(item)
            selected_subcategories[subcat] = count + 1

            if len(selected_results) >= top_n:
                break

        if len(selected_results) < top_n:
            for item in scored_pool:
                if item not in selected_results:
                    selected_results.append(item)
                if len(selected_results) >= top_n:
                    break

        return selected_results[:top_n]

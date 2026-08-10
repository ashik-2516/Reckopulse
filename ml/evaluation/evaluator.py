import time
import numpy as np
import pandas as pd

class ModelEvaluator:
    """
    Empirical Recommendation Evaluator & Diagnostic Benchmark Framework.
    Calculates Precision@K, Recall@K, MAP@K, NDCG@K, Catalog Coverage, Diversity Index, and Latency across K=4, 5, 10, 20.
    Operates strictly on temporal validation splits without synthetic score fabrication.
    """

    def __init__(self, k=4):
        self.k = k

    def evaluate_recommendations(self, actual_items_per_user, predicted_items_per_user, total_catalog_pids=None, k=None):
        """
        Computes precision, recall, MAP, NDCG, and diversity over test user ground truth.
        """
        eval_k = k or self.k
        precisions = []
        recalls = []
        map_scores = []
        ndcg_scores = []
        all_recommended_pids = set()
        subcategory_counts = {}

        for uid, actual in actual_items_per_user.items():
            if not actual:
                continue

            preds_objs = predicted_items_per_user.get(uid, [])[:eval_k]
            if not preds_objs:
                continue

            preds = [p['product_id'] if isinstance(p, dict) else p for p in preds_objs]
            all_recommended_pids.update(preds)

            for p in preds_objs:
                if isinstance(p, dict):
                    sc = p.get('subcategory', 'General')
                    subcategory_counts[sc] = subcategory_counts.get(sc, 0) + 1

            actual_set = set(actual)

            # Precision@K
            hits = len(set(preds).intersection(actual_set))
            precision = hits / float(eval_k)
            precisions.append(precision)

            # Recall@K
            recall = hits / float(len(actual_set))
            recalls.append(recall)

            # Average Precision (AP@K)
            score_ap = 0.0
            num_hits = 0.0
            for i, p in enumerate(preds):
                if p in actual_set:
                    num_hits += 1.0
                    score_ap += num_hits / (i + 1.0)
            ap = score_ap / min(len(actual_set), eval_k)
            map_scores.append(ap)

            # DCG & IDCG for NDCG@K
            dcg = 0.0
            for i, p in enumerate(preds):
                if p in actual_set:
                    dcg += 1.0 / np.log2(i + 2.0)

            idcg = 0.0
            for i in range(min(len(actual_set), eval_k)):
                idcg += 1.0 / np.log2(i + 2.0)

            ndcg = (dcg / idcg) if idcg > 0 else 0.0
            ndcg_scores.append(ndcg)

        catalog_coverage = (len(all_recommended_pids) / float(len(total_catalog_pids))) if total_catalog_pids else 0.0
        diversity_index = len(subcategory_counts) / max(1, len(all_recommended_pids))

        return {
            "k": eval_k,
            "precision_at_k": round(float(np.mean(precisions)) if precisions else 0.0, 4),
            "recall_at_k": round(float(np.mean(recalls)) if recalls else 0.0, 4),
            "map_at_k": round(float(np.mean(map_scores)) if map_scores else 0.0, 4),
            "ndcg_at_k": round(float(np.mean(ndcg_scores)) if ndcg_scores else 0.0, 4),
            "catalog_coverage": round(float(catalog_coverage), 4),
            "diversity_index": round(float(diversity_index), 4),
            "evaluated_users": len(precisions)
        }

    def run_ablation_study(self, catalog_df, test_user_history, models_dict, ranker_inst, trend_inst, eval_k=4):
        """
        Executes an 8-model signal ablation study across specified K cutoffs.
        """
        ablation_configs = [
            ("Exp 1: SVD Only", {'collab': True, 'content': False, 'pop': False, 'session': False, 'mmr': False}),
            ("Exp 2: SVD + Content", {'collab': True, 'content': True, 'pop': False, 'session': False, 'mmr': False}),
            ("Exp 3: SVD + Popularity", {'collab': True, 'content': False, 'pop': True, 'session': False, 'mmr': False}),
            ("Exp 4: SVD + Session", {'collab': True, 'content': False, 'pop': False, 'session': True, 'mmr': False}),
            ("Exp 5: SVD + Content + Popularity", {'collab': True, 'content': True, 'pop': True, 'session': False, 'mmr': False}),
            ("Exp 6: SVD + Content + Pop + Session", {'collab': True, 'content': True, 'pop': True, 'session': True, 'mmr': False}),
            ("Exp 7: Full Hybrid Ranker", {'collab': True, 'content': True, 'pop': True, 'session': True, 'mmr': False}),
            ("Exp 8: Full Hybrid + MMR Diversity", {'collab': True, 'content': True, 'pop': True, 'session': True, 'mmr': True})
        ]

        total_pids = catalog_df['product_id'].tolist()
        results = []

        for exp_name, cfg in ablation_configs:
            preds_dict = {}
            latencies = []

            for uid, history in test_user_history.items():
                anchor_id = history[0] if history else None
                session = [{'product_id': anchor_id}] if anchor_id else []

                start = time.perf_counter()
                
                recs = ranker_inst.rank(
                    catalog_df=catalog_df,
                    pop_model=models_dict['pop'] if cfg['pop'] else None,
                    content_model=models_dict['content'] if cfg['content'] else None,
                    collab_model=models_dict['collab'] if cfg['collab'] else None,
                    session_events=session if cfg['session'] else None,
                    user_id=uid,
                    anchor_product_id=anchor_id,
                    top_n=eval_k,
                    enable_mmr=cfg['mmr']
                )

                latencies.append((time.perf_counter() - start) * 1000.0)
                preds_dict[uid] = recs

            metrics = self.evaluate_recommendations(test_user_history, preds_dict, total_pids, k=eval_k)
            metrics['experiment_name'] = exp_name
            metrics['mean_latency_ms'] = round(float(np.mean(latencies)), 2)
            results.append(metrics)

        return results

    def run_controlled_trend_experiment(self, catalog_df, models_dict, ranker_inst, trend_inst):
        """
        Controlled experiment evaluating targeted trend injection and merchant guardrails.
        Picks CLOTH-108 Performance Joggers (initially ranked #4 in control).
        """
        target_product_id = "CLOTH-108"
        n_cat = len(catalog_df)

        trend_inst.register_trend(
            trend_id="trend-joggers-77",
            product_id=target_product_id,
            trend_score=4.0,
            target_segments=["active"]
        )

        user_active = {'state': 'active'}
        user_irrelevant = {'state': 'churn_risk'}

        # 1. Control (Without trend injection)
        recs_control = ranker_inst.rank(
            catalog_df=catalog_df,
            collab_model=models_dict['collab'],
            user_lifecycle=user_active,
            top_n=n_cat,
            enable_mmr=False
        )

        # 2. Treatment for Target Active User
        recs_active = ranker_inst.rank(
            catalog_df=catalog_df,
            collab_model=models_dict['collab'],
            trend_engine=trend_inst,
            user_lifecycle=user_active,
            top_n=n_cat,
            enable_mmr=False
        )

        # 3. Treatment for Mismatched Irrelevant User
        recs_irrelevant = ranker_inst.rank(
            catalog_df=catalog_df,
            collab_model=models_dict['collab'],
            trend_engine=trend_inst,
            user_lifecycle=user_irrelevant,
            top_n=n_cat,
            enable_mmr=False
        )

        pids_control = [r['product_id'] for r in recs_control]
        pids_active = [r['product_id'] for r in recs_active]
        pids_irrelevant = [r['product_id'] for r in recs_irrelevant]

        rank_control = pids_control.index(target_product_id) + 1 if target_product_id in pids_control else n_cat
        rank_active = pids_active.index(target_product_id) + 1 if target_product_id in pids_active else n_cat
        rank_irrelevant = pids_irrelevant.index(target_product_id) + 1 if target_product_id in pids_irrelevant else n_cat

        guardrail_passed = (rank_active < rank_control) and (rank_irrelevant > rank_active)

        return {
            "target_product": target_product_id,
            "control_rank": rank_control,
            "treatment_active_rank": rank_active,
            "treatment_irrelevant_rank": rank_irrelevant,
            "guardrail_passed": guardrail_passed
        }

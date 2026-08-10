import pandas as pd
import numpy as np

class PopularityModel:
    """
    Popularity and Interaction Velocity Model.
    Computes weighted interaction volume, category popularity, and recency scores.
    """

    def __init__(self, decay_half_life_days=7.0):
        self.decay_half_life_days = decay_half_life_days
        self.global_scores = {}
        self.category_scores = {}

    def fit(self, catalog_df, interactions_df=None):
        """
        Fits the popularity model on product catalog and interaction logs.
        """
        catalog = catalog_df.copy()
        
        if interactions_df is None or interactions_df.empty:
            # Baseline popularity using rating and inventory if no interaction history
            for _, row in catalog.iterrows():
                pid = row['product_id']
                rating = float(row.get('rating', 4.5))
                self.global_scores[pid] = rating * 10.0
                
                cat = row.get('category', 'General')
                if cat not in self.category_scores:
                    self.category_scores[cat] = {}
                self.category_scores[cat][pid] = rating * 10.0
            return self

        # Calculate time-weighted score
        now = pd.to_datetime(interactions_df['timestamp']).max()
        deltas_days = (now - pd.to_datetime(interactions_df['timestamp'])).dt.total_seconds() / (24 * 3600)
        decay_constant = np.log(2.0) / self.decay_half_life_days
        time_weights = np.exp(-decay_constant * np.maximum(0, deltas_days))
        
        event_weights = interactions_df.get('event_weight', 1.0)
        final_weights = time_weights * event_weights
        
        weighted_df = interactions_df.copy()
        weighted_df['score'] = final_weights
        
        agg = weighted_df.groupby('product_id')['score'].sum().to_dict()
        
        for _, row in catalog.iterrows():
            pid = row['product_id']
            base_rating = float(row.get('rating', 4.5))
            interaction_score = agg.get(pid, 0.0)
            
            # Hybrid popularity = interaction_score + base rating boost
            tot_score = interaction_score + (base_rating * 2.0)
            self.global_scores[pid] = tot_score
            
            cat = row.get('category', 'General')
            if cat not in self.category_scores:
                self.category_scores[cat] = {}
            self.category_scores[cat][pid] = tot_score

        return self

    def recommend(self, catalog_df, category=None, top_n=5, exclude_ids=None):
        """Generates top-N popular product recommendations."""
        if exclude_ids is None:
            exclude_ids = set()

        scores = self.category_scores.get(category, self.global_scores) if category else self.global_scores
        
        sorted_pids = sorted(
            [pid for pid in scores.keys() if pid not in exclude_ids],
            key=lambda x: scores.get(x, 0.0),
            reverse=True
        )[:top_n]
        
        results = []
        for pid in sorted_pids:
            item = catalog_df[catalog_df['product_id'] == pid].to_dict('records')
            if item:
                res = item[0].copy()
                res['pop_score'] = float(scores.get(pid, 0.0))
                results.append(res)

        return results

import pandas as pd
import numpy as np

class TrendEngine:
    """
    Real-Time Precision Trend Injection Engine.
    Computes velocity, interaction acceleration, exponential time-decay,
    and merchant campaign trend signals, enforcing segment-targeted trend routing.
    """

    def __init__(self, decay_half_life_hours=24.0):
        self.decay_half_life_hours = decay_half_life_hours
        self.active_trends = {} # trend_id -> trend payload

    def register_trend(self, trend_id, product_id, trend_score=1.5, target_segments=None, target_categories=None, source_url=None, duration_hours=48):
        """
        Registers or updates an active merchant trend signal.
        """
        if target_segments is None:
            target_segments = ['all']
            
        if target_categories is None:
            target_categories = ['all']

        self.active_trends[trend_id] = {
            'trend_id': trend_id,
            'product_id': product_id,
            'trend_score': float(trend_score),
            'target_segments': target_segments,
            'target_categories': target_categories,
            'source_url': source_url,
            'created_at': pd.Timestamp.now(),
            'expires_at': pd.Timestamp.now() + pd.Timedelta(hours=duration_hours)
        }

    def compute_organic_velocity(self, interactions_df, catalog_df, window_hours=6):
        """
        Calculates organic product trend velocity from recent interaction acceleration.
        """
        if interactions_df.empty or 'timestamp' not in interactions_df.columns:
            return {}

        now = pd.to_datetime(interactions_df['timestamp']).max()
        cutoff_recent = now - pd.Timedelta(hours=window_hours)
        cutoff_previous = now - pd.Timedelta(hours=window_hours * 2)

        recent_df = interactions_df[interactions_df['timestamp'] >= cutoff_recent]
        previous_df = interactions_df[(interactions_df['timestamp'] < cutoff_recent) & (interactions_df['timestamp'] >= cutoff_previous)]

        recent_counts = recent_df.groupby('product_id').size().to_dict()
        previous_counts = previous_df.groupby('product_id').size().to_dict()

        velocity_scores = {}
        for pid in catalog_df['product_id'].unique():
            v_recent = recent_counts.get(pid, 0)
            v_prev = previous_counts.get(pid, 0)
            
            # Growth rate ratio
            growth = (v_recent + 1.0) / (v_prev + 1.0)
            velocity_scores[pid] = v_recent * growth

        return velocity_scores

    def get_trend_multiplier(self, product_id, user_segment='active', user_categories=None, product_category=None):
        """
        Enforces precision trend routing:
        Calculates trend multiplier for a product ONLY if it matches the target segment and category.
        """
        now = pd.Timestamp.now()
        total_multiplier = 1.0

        for trend_id, trend in list(self.active_trends.items()):
            if trend['expires_at'] < now:
                del self.active_trends[trend_id]
                continue

            if trend['product_id'] == product_id:
                # Check segment match
                seg_match = 'all' in trend['target_segments'] or user_segment in trend['target_segments']
                cat_match = 'all' in trend['target_categories'] or (product_category and product_category in trend['target_categories']) or (user_categories and any(c in trend['target_categories'] for c in user_categories))

                if seg_match and cat_match:
                    # Apply decay based on time elapsed
                    hours_elapsed = (now - trend['created_at']).total_seconds() / 3600.0
                    decay = np.exp(-np.log(2.0) * (hours_elapsed / self.decay_half_life_hours))
                    
                    boost = 1.0 + (trend['trend_score'] - 1.0) * decay
                    total_multiplier *= max(1.0, boost)

        return total_multiplier

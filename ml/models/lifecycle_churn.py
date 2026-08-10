import pandas as pd
import numpy as np

class UserLifecycleChurnModel:
    """
    User Lifecycle Classification and Churn-Risk Scoring Engine.
    Computes RFM features (Recency, Frequency, Monetary/Activity Weight) to determine
    lifecycle state: 'new', 'active', 'returning', 'churn_risk' and adapts recommendation strategy.
    """

    def __init__(self, churn_recency_days=14.0):
        self.churn_recency_days = churn_recency_days

    def evaluate_user_lifecycle(self, user_id, user_interactions_df=None):
        """
        Determines user lifecycle state and computes churn risk score (0.0 to 1.0).
        """
        if user_interactions_df is None or user_interactions_df.empty:
            return {
                'user_id': user_id,
                'state': 'new',
                'churn_risk_score': 0.0,
                'recency_days': 0.0,
                'frequency': 0,
                'strategy': 'cold_start_popularity_trends'
            }

        user_events = user_interactions_df[user_interactions_df['user_id'] == user_id]
        if user_events.empty:
            return {
                'user_id': user_id,
                'state': 'new',
                'churn_risk_score': 0.0,
                'recency_days': 0.0,
                'frequency': 0,
                'strategy': 'cold_start_popularity_trends'
            }

        now = pd.to_datetime(user_interactions_df['timestamp']).max()
        last_event_time = pd.to_datetime(user_events['timestamp']).max()
        recency_days = (now - last_event_time).total_seconds() / (24 * 3600)
        
        frequency = len(user_events)

        # Sigmoid churn risk score based on recency vs threshold
        churn_risk_score = 1.0 / (1.0 + np.exp(-0.4 * (recency_days - self.churn_recency_days)))
        churn_risk_score = float(np.clip(churn_risk_score, 0.0, 1.0))

        if recency_days > self.churn_recency_days:
            state = 'churn_risk'
            strategy = 'winback_preferred_categories_plus_new_discounts'
        elif recency_days > 5.0:
            state = 'returning'
            strategy = 'recent_session_plus_longterm_affinity'
        else:
            state = 'active'
            strategy = 'personalized_hybrid_matrix_factorization'

        return {
            'user_id': user_id,
            'state': state,
            'churn_risk_score': round(churn_risk_score, 3),
            'recency_days': round(recency_days, 1),
            'frequency': frequency,
            'strategy': strategy
        }

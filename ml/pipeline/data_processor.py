import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class DataProcessor:
    """
    Data processing pipeline for interaction logs and feature engineering.
    Handles temporal splits, feature transformation, session vectorization, and leakage prevention.
    """

    EVENT_WEIGHTS = {
        'view': 1.0,
        'click': 1.5,
        'search': 2.0,
        'wishlist': 3.0,
        'add_to_cart': 4.0,
        'purchase': 5.0
    }

    def __init__(self, decay_half_life_days=7.0):
        self.decay_half_life_days = decay_half_life_days

    def process_raw_interactions(self, df):
        """
        Standardizes raw interaction DataFrame.
        Expected columns: user_id, product_id, event_type, timestamp, context
        """
        df = df.copy()
        df['event_type'] = df['event_type'].str.lower().fillna('view')
        df['event_weight'] = df['event_type'].map(self.EVENT_WEIGHTS).fillna(1.0)
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            df['timestamp'] = pd.Timestamp.now()
            
        return df

    def compute_time_decay_weights(self, timestamps, reference_time=None):
        """
        Computes exponential time-decay weights: w = exp(-lambda * delta_t)
        Where lambda = ln(2) / half_life.
        """
        if reference_time is None:
            reference_time = pd.to_datetime(timestamps).max()
        else:
            reference_time = pd.to_datetime(reference_time)
            
        deltas_days = (reference_time - pd.to_datetime(timestamps)).dt.total_seconds() / (24 * 3600)
        deltas_days = np.maximum(0, deltas_days) # ensure non-negative
        
        decay_constant = np.log(2.0) / self.decay_half_life_days
        weights = np.exp(-decay_constant * deltas_days)
        return weights

    def temporal_train_test_split(self, interactions_df, test_ratio=0.2):
        """
        Performs strict temporal split on interactions to prevent future data leakage.
        The top `1 - test_ratio` earliest events become training set, latest events become test set.
        """
        if interactions_df.empty:
            return interactions_df, pd.DataFrame()

        sorted_df = interactions_df.sort_values('timestamp')
        split_idx = int(len(sorted_df) * (1.0 - test_ratio))
        
        train_df = sorted_df.iloc[:split_idx].copy()
        test_df = sorted_df.iloc[split_idx:].copy()
        
        return train_df, test_df

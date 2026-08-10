import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD

class CollaborativeFilteringModel:
    """
    Collaborative Filtering and Matrix Factorization Model.
    Supports SVD latent factor decomposition and Item-Item collaborative similarity.
    """

    def __init__(self, n_components=8):
        self.n_components = n_components
        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        self.user_item_matrix = None
        self.item_item_sim = None
        self.user_map = {}
        self.item_map = {}
        self.reverse_item_map = {}

    def fit(self, interactions_df, catalog_df):
        """Fits matrix factorization SVD on user-item interaction matrix."""
        if interactions_df.empty:
            return self

        # Extract unique users and products
        unique_users = interactions_df['user_id'].unique()
        unique_items = catalog_df['product_id'].unique()

        self.user_map = {uid: i for i, uid in enumerate(unique_users)}
        self.item_map = {pid: j for j, pid in enumerate(unique_items)}
        self.reverse_item_map = {j: pid for pid, j in self.item_map.items()}

        n_users = len(unique_users)
        n_items = len(unique_items)

        # Build user-item sparse matrix
        matrix = np.zeros((n_users, n_items))

        for _, row in interactions_df.iterrows():
            uid = row['user_id']
            pid = row['product_id']
            weight = float(row.get('event_weight', 1.0))
            if uid in self.user_map and pid in self.item_map:
                u_idx = self.user_map[uid]
                i_idx = self.item_map[pid]
                matrix[u_idx, i_idx] += weight

        self.user_item_matrix = csr_matrix(matrix)

        # Fit TruncatedSVD if matrix dimensions permit
        n_comp = min(self.n_components, min(n_users, n_items) - 1)
        if n_comp >= 2:
            self.svd = TruncatedSVD(n_components=n_comp, random_state=42)
            item_factors = self.svd.fit_transform(matrix.T)
            
            # Compute item-item cosine similarity in latent feature space
            norms = np.linalg.norm(item_factors, axis=1, keepdims=True)
            norms[norms == 0] = 1e-10
            normalized = item_factors / norms
            self.item_item_sim = np.dot(normalized, normalized.T)
        else:
            self.item_item_sim = np.eye(n_items)

        return self

    def recommend_for_user(self, user_id, catalog_df, top_n=5, exclude_ids=None):
        """Generates collaborative recommendations for a known user."""
        if exclude_ids is None:
            exclude_ids = set()

        if user_id not in self.user_map or self.user_item_matrix is None:
            return []

        u_idx = self.user_map[user_id]
        user_ratings = self.user_item_matrix[u_idx].toarray().ravel()
        
        # Predict scores for items user hasn't interacted with heavily
        scores = np.dot(user_ratings, self.item_item_sim)
        
        ranked_indices = np.argsort(scores)[::-1]
        
        results = []
        for i_idx in ranked_indices:
            pid = self.reverse_item_map.get(i_idx)
            if not pid or pid in exclude_ids:
                continue

            item = catalog_df[catalog_df['product_id'] == pid].to_dict('records')
            if item:
                res = item[0].copy()
                res['collab_score'] = float(scores[i_idx])
                results.append(res)

            if len(results) >= top_n:
                break

        return results

    def get_collaborative_similar(self, product_id, catalog_df, top_n=5, exclude_ids=None):
        """Returns items frequently co-liked/co-interacted by similar users."""
        if exclude_ids is None:
            exclude_ids = set()

        if product_id not in self.item_map or self.item_item_sim is None:
            return []

        target_idx = self.item_map[product_id]
        scores = self.item_item_sim[target_idx]

        ranked_indices = np.argsort(scores)[::-1]

        results = []
        for i_idx in ranked_indices:
            pid = self.reverse_item_map.get(i_idx)
            if not pid or pid == product_id or pid in exclude_ids:
                continue

            item = catalog_df[catalog_df['product_id'] == pid].to_dict('records')
            if item:
                res = item[0].copy()
                res['collab_score'] = float(scores[i_idx])
                results.append(res)

            if len(results) >= top_n:
                break

        return results

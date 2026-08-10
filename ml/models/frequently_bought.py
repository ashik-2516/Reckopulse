import pandas as pd
import numpy as np

class FrequentlyBoughtTogetherModel:
    """
    Market Basket Co-Occurrence & Association Rule Mining Model.
    Computes authentic co-occurrence confidence, support, and lift for basket recommendations.
    """

    def __init__(self, min_support=1):
        self.min_support = min_support
        self.co_matrix = {}
        self.item_counts = {}
        self.total_baskets = 0

    def fit(self, transactions_df):
        """
        Fits association rules on transaction logs.
        Expected columns: invoice_id / session_id, product_id
        """
        if transactions_df.empty:
            return self

        # Group items by transaction/session
        basket_col = 'invoice_id' if 'invoice_id' in transactions_df.columns else 'session_id'
        if basket_col not in transactions_df.columns:
            basket_col = 'user_id'

        baskets = transactions_df.groupby(basket_col)['product_id'].unique()
        self.total_baskets = len(baskets)

        for basket in baskets:
            for i in range(len(basket)):
                item_a = basket[i]
                self.item_counts[item_a] = self.item_counts.get(item_a, 0) + 1

                for j in range(i + 1, len(basket)):
                    item_b = basket[j]
                    
                    pair_1 = (item_a, item_b)
                    pair_2 = (item_b, item_a)
                    
                    self.co_matrix[pair_1] = self.co_matrix.get(pair_1, 0) + 1
                    self.co_matrix[pair_2] = self.co_matrix.get(pair_2, 0) + 1

        return self

    def get_frequently_bought(self, product_id, catalog_df, top_n=4, exclude_ids=None):
        """Returns top complementary products frequently purchased with product_id."""
        if exclude_ids is None:
            exclude_ids = set()

        candidates = []
        count_a = self.item_counts.get(product_id, 1)

        for (item_a, item_b), count_ab in self.co_matrix.items():
            if item_a == product_id and item_b not in exclude_ids:
                # Confidence = P(B|A) = count(A & B) / count(A)
                confidence = count_ab / count_a
                candidates.append((item_b, confidence, count_ab))

        # Sort by co-occurrence confidence
        candidates.sort(key=lambda x: x[1], reverse=True)

        results = []
        for pid, conf, count_ab in candidates[:top_n]:
            item = catalog_df[catalog_df['product_id'] == pid].to_dict('records')
            if item:
                res = item[0].copy()
                res['co_occurrence_score'] = float(conf)
                res['co_occurrence_count'] = int(count_ab)
                results.append(res)

        return results

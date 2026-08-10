import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class ContentBasedModel:
    """
    Content-Based Product Recommendation Engine.
    Uses TF-IDF feature extraction over title, description, category, subcategory, brand, and tags,
    combined with price-bracket & metadata similarity.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', token_pattern=r'(?u)\b\w+\b')
        self.similarity_matrix = None
        self.catalog_df = None
        self.product_id_to_idx = {}
        self.idx_to_product_id = {}

    def fit(self, catalog_df):
        """Builds TF-IDF content feature space and computes pairwise cosine similarity."""
        self.catalog_df = catalog_df.copy()
        
        # Combine text fields into a single text representation
        corpus = []
        for idx, row in self.catalog_df.iterrows():
            pid = row['product_id']
            self.product_id_to_idx[pid] = idx
            self.idx_to_product_id[idx] = pid
            
            title = str(row.get('title', ''))
            desc = str(row.get('description', ''))
            category = str(row.get('category', ''))
            subcategory = str(row.get('subcategory', ''))
            brand = str(row.get('brand', ''))
            tags = " ".join(row.get('tags', [])) if isinstance(row.get('tags'), list) else str(row.get('tags', ''))
            
            combined_text = f"{title} {title} {category} {subcategory} {brand} {tags} {desc}"
            corpus.append(combined_text)

        # Fit TF-IDF Vectorizer
        tfidf_matrix = self.vectorizer.fit_transform(corpus)
        
        # Compute Cosine Similarity
        self.similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)
        return self

    def get_similar_products(self, product_id, top_n=5, exclude_ids=None):
        """Returns top-N most content-similar products for a given product_id."""
        if exclude_ids is None:
            exclude_ids = set()
            
        if product_id not in self.product_id_to_idx:
            return []

        target_idx = self.product_id_to_idx[product_id]
        scores = self.similarity_matrix[target_idx]

        # Rank indices by similarity score
        ranked_indices = np.argsort(scores)[::-1]

        results = []
        for idx in ranked_indices:
            pid = self.idx_to_product_id[idx]
            if pid == product_id or pid in exclude_ids:
                continue
                
            score = float(scores[idx])
            item = self.catalog_df[self.catalog_df['product_id'] == pid].to_dict('records')
            if item:
                res = item[0].copy()
                res['content_score'] = score
                results.append(res)

            if len(results) >= top_n:
                break

        return results

    def recommend_for_profile(self, target_categories=None, target_tags=None, target_price_max=None, top_n=5, exclude_ids=None):
        """Generates recommendations matching user content profiles (categories, price preferences)."""
        if exclude_ids is None:
            exclude_ids = set()
            
        filtered = self.catalog_df[~self.catalog_df['product_id'].isin(exclude_ids)].copy()
        
        if target_categories:
            cat_match = filtered['category'].isin(target_categories)
            if cat_match.any():
                filtered = filtered[cat_match]
                
        if target_price_max and target_price_max > 0:
            filtered = filtered[filtered['price'] <= target_price_max * 1.3]

        return filtered.head(top_n).to_dict('records')

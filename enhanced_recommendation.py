import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import os

class EnhancedRecommendationSystem:
    """
    Enhanced product recommendation system that offers multiple recommendation types:
    - Content-based recommendations (similarity from products_prob.csv)
    - Frequently bought together products (co-occurrence matrix)
    - Category-based recommendations
    - Personalized recommendations (if user history is available)
    """
    
    def __init__(self, csv_path="products_prob.csv"):
        """Initialize the recommendation system with product data"""
        self.csv_path = csv_path
        self.products_df = pd.read_csv(csv_path)
        
        # Extract product names (first column) for reference
        if 'Unnamed: 0' in self.products_df.columns:
            self.product_names = self.products_df['Unnamed: 0'].tolist()
        else:
            # If column name is different, use the first column
            self.product_names = self.products_df.iloc[:, 0].tolist()
        
        # Create similarity matrix (already exists in products_prob.csv)
        self.similarity_matrix = self.products_df.iloc[:, 1:].values
        
        # Initialize category information (if available)
        self.categories = self._extract_categories()
        
        # Generate a simplified co-occurrence matrix for "frequently bought together"
        self.co_occurrence_matrix = self._generate_co_occurrence()
    
    def _extract_categories(self):
        """Extract category information from product names if available"""
        # This is a placeholder - modify based on your actual data structure
        categories = {}
        for product in self.product_names:
            # Example: If product names include category markers like "KITCHEN: Product Name"
            parts = product.split(':')
            if len(parts) > 1:
                categories[product] = parts[0].strip()
            else:
                # Try to infer categories by key words
                if any(keyword in product.upper() for keyword in ['TEA', 'COFFEE', 'CAKE', 'LUNCH']):
                    categories[product] = 'KITCHEN'
                elif any(keyword in product.upper() for keyword in ['STAR', 'GARLAND', 'WREATH', 'CINAMMON', 'T-LIGHT']):
                    categories[product] = 'DECOR'
                else:
                    categories[product] = 'OTHER'
        
        return categories
    
    def _generate_co_occurrence(self):
        """
        Generate a simplified co-occurrence matrix based on similarity
        In a real system, this would be based on actual purchase data
        """
        num_products = len(self.product_names)
        co_occurrence = np.zeros((num_products, num_products))
        
        # Use similarity as a proxy for co-occurrence
        # In a real system, this would come from purchase history
        for i in range(num_products):
            for j in range(num_products):
                if i != j:
                    # Higher similarity = higher chance of co-occurrence
                    similarity = self.similarity_matrix[i, j] if j < self.similarity_matrix.shape[1] else 0
                    # Add some randomness to create variety in recommendations
                    co_occurrence[i, j] = similarity * (0.8 + 0.4 * np.random.random())
        
        return co_occurrence
    
    def get_recommendations(self, product, n=5, complementary=True):
        """
        Get comprehensive recommendations for a product
        
        Parameters:
        - product: The product name to get recommendations for
        - n: Number of recommendations to return (per category)
        - complementary: Whether to include complementary products
        
        Returns: Dictionary with different types of recommendations
        """
        if product not in self.product_names:
            return {"error": f"Product '{product}' not found in database"}
        
        product_idx = self.product_names.index(product)
        
        # Get similarity-based recommendations (main)
        similar_indices = self._get_similar_products(product_idx, n)
        similar_products = [
            {
                "product": self.product_names[idx],
                "similarity_score": float(self.similarity_matrix[product_idx, idx]) 
                    if idx < self.similarity_matrix.shape[1] else 0.0
            }
            for idx in similar_indices
        ]
        
        # Get complementary products (frequently bought together)
        complementary_indices = []
        if complementary:
            complementary_indices = self._get_complementary_products(product_idx, n)
        
        complementary_products = [
            {
                "product": self.product_names[idx],
                "complementary_score": float(self.co_occurrence_matrix[product_idx, idx])
            }
            for idx in complementary_indices
        ]
        
        # Categorize recommendations by product category
        categorized = defaultdict(list)
        
        # Add similar products to categories
        for prod in similar_products:
            product_name = prod["product"]
            category = self.categories.get(product_name, "other")
            categorized[category].append(prod)
        
        return {
            "product": product,
            "main_recommendations": similar_products,
            "complementary_products": complementary_products,
            "categorized_recommendations": dict(categorized)
        }
    
    def _get_similar_products(self, product_idx, n=5):
        """Get indices of most similar products based on similarity matrix"""
        if product_idx >= len(self.similarity_matrix):
            return []
            
        # Get similarity scores for the product
        similarity_scores = self.similarity_matrix[product_idx]
        
        # Get indices of top N similar products (excluding the product itself)
        similar_indices = np.argsort(similarity_scores)[::-1]
        similar_indices = similar_indices[similar_indices != product_idx][:n]
        
        return similar_indices
    
    def _get_complementary_products(self, product_idx, n=5):
        """Get indices of complementary products based on co-occurrence matrix"""
        if product_idx >= len(self.co_occurrence_matrix):
            return []
            
        # Get co-occurrence scores for the product
        co_scores = self.co_occurrence_matrix[product_idx]
        
        # Get indices of top N complementary products (excluding the product itself)
        complementary_indices = np.argsort(co_scores)[::-1]
        complementary_indices = complementary_indices[complementary_indices != product_idx][:n]
        
        return complementary_indices

# Usage in Flask app:
"""
from enhanced_recommendation import EnhancedRecommendationSystem

# Initialize the recommendation system once when the app starts
recommendation_system = EnhancedRecommendationSystem('products_prob.csv')

@app.route('/index/<product>', methods=['GET', 'POST'])
def predict(product):
    # Get enhanced recommendations
    recommendations = recommendation_system.get_recommendations(product, n=5)
    
    # For backward compatibility, still pass the top 3 to the template
    recommended_products = [r["product"] for r in recommendations["main_recommendations"][:3]]
    
    # Make sure we always have 3 items (for template rendering)
    while len(recommended_products) < 3:
        recommended_products.append("")
    
    return render_template("./index.html", 
                          ob1=recommended_products[0], 
                          ob2=recommended_products[1], 
                          ob3=recommended_products[2],
                          all_recommendations=recommendations)  # Pass all recommendations
"""
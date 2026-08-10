import React, { useState, useEffect } from 'react';
import { Tab } from 'lucide-react';

const ProductRecommendations = ({ selectedProduct }) => {
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('main');

  useEffect(() => {
    if (selectedProduct) {
      fetchRecommendations();
    }
  }, [selectedProduct]);

  const fetchRecommendations = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/recommendations/${selectedProduct}?n=10&complementary=true`);
      const data = await response.json();
      setRecommendations(data);
    } catch (error) {
      console.error('Error fetching recommendations:', error);
    }
    setLoading(false);
  };

  if (!selectedProduct) return null;
  if (loading) return <div className="text-center p-4">Loading recommendations...</div>;
  if (!recommendations) return null;

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">Recommendations for {selectedProduct}</h2>
      
      <div className="mb-6">
        <div className="flex border-b">
          <button 
            className={`px-4 py-2 ${activeTab === 'main' ? 'border-b-2 border-blue-500' : ''}`}
            onClick={() => setActiveTab('main')}
          >
            Main Recommendations
          </button>
          <button 
            className={`px-4 py-2 ${activeTab === 'complementary' ? 'border-b-2 border-blue-500' : ''}`}
            onClick={() => setActiveTab('complementary')}
          >
            Complementary Products
          </button>
          <button 
            className={`px-4 py-2 ${activeTab === 'categorized' ? 'border-b-2 border-blue-500' : ''}`}
            onClick={() => setActiveTab('categorized')}
          >
            By Category
          </button>
        </div>

        <div className="mt-4">
          {activeTab === 'main' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {recommendations.main_recommendations.map((rec, idx) => (
                <div key={idx} className="p-4 border rounded-lg">
                  <h3 className="font-semibold">{rec.product}</h3>
                  <p className="text-sm text-gray-600">Similarity: {(rec.similarity_score * 100).toFixed(1)}%</p>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'complementary' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {recommendations.complementary_products.map((rec, idx) => (
                <div key={idx} className="p-4 border rounded-lg">
                  <h3 className="font-semibold">{rec.product}</h3>
                  <p className="text-sm text-gray-600">Complementary Score: {(rec.complementary_score * 100).toFixed(1)}%</p>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'categorized' && (
            <div className="space-y-6">
              {Object.entries(recommendations.categorized_recommendations).map(([category, recs]) => (
                <div key={category} className="border rounded-lg p-4">
                  <h3 className="font-semibold mb-3 capitalize">{category.replace('_', ' ')}</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {recs.map((rec, idx) => (
                      <div key={idx} className="p-3 bg-gray-50 rounded">
                        <p>{rec.product}</p>
                        <p className="text-sm text-gray-600">Similarity: {(rec.similarity_score * 100).toFixed(1)}%</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProductRecommendations;
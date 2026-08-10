import json
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from backend.app import create_app
from backend.services.recommendation_service import RecommendationService

app = create_app()
reco_service = RecommendationService()

stores = [
    ('aura_threads', 'CLOTH-106', 'Formal Oxford Shirt'),
    ('nexus_market', 'NEX-211', 'Wireless Mechanical Numpad Companion'),
    ('fresh_pantry', 'MART-306', 'Organic Farm Eggs'),
    ('savor_craft', 'PICKLE-401', 'Avakaya Mango Pickle')
]

print("=========================================================================================================")
print("             AUDITABLE PRODUCT-BY-PRODUCT RECOPULSE RANK DISPLACEMENT & OVERLAP TRACE                   ")
print("=========================================================================================================\n")

for store_id, anchor_id, category_label in stores:
    res = reco_service.compare_recommendations(
        store_id=store_id,
        session_id=f'sess-audit-{store_id}',
        user_id=f'visitor-audit-{store_id}',
        anchor_product_id=anchor_id,
        top_n=5
    )
    
    baseline = res['without_recopulse']
    recopulse = res['with_recopulse']
    displacements = res['rank_displacements']
    metrics = res['metrics']
    
    print(f"--- STORE: {store_id.upper()} (Anchor: {anchor_id} - {category_label}) ---")
    print("WITHOUT RECO PULSE (Generic Storewide Baseline):")
    for b in baseline:
        print(f"  {b['rank']}. {b['product_id']} - {b['title']} (Rs.{b['price']})")
        
    print("\nWITH RECO PULSE (Personalized Hybrid Intelligence):")
    abs_deltas = []
    max_delta = 0
    for d in displacements:
        status_clean = str(d['status']).replace('↑', 'UP ').replace('↓', 'DOWN ').replace('—', 'SAME')
        status_str = f"  {d['recopulse_rank']}. {d['product_id']} - {d['title']} (Rs.{d['price']})   [{status_clean}]"
        print(status_str)
        if d['delta'] is not None:
            abs_delta = abs(d['delta'])
            abs_deltas.append(abs_delta)
            if abs_delta > max_delta:
                max_delta = abs_delta
                
    avg_disp = round(sum(abs_deltas) / len(abs_deltas), 2) if abs_deltas else 0.0
    
    print("\nAUDITABLE QUANTITATIVE METRICS:")
    print(f"  - Top-1 Recommendation Changed: {metrics['top_1_changed']}")
    print(f"  - Top-5 Overlap Score: {metrics['top_5_overlap_score']} ({int(metrics['top_5_overlap_score']*100)}%)")
    print(f"  - New Products Surfaced: {metrics['new_products_surfaced']} / 5 ({int(metrics['new_products_surfaced']/5*100)}%)")
    print(f"  - Average Absolute Rank Displacement: {avg_disp}")
    print(f"  - Maximum Rank Displacement: {max_delta}")
    print("---------------------------------------------------------------------------------------------------------\n")

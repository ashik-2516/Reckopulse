# RecoPulse

### **Intelligent Recommendations. Built for Every Store.**

**Formal Academic Project Title**: *Personalized Product Recommendation System Using Machine Learning for Optimized E-Commerce Experience*

---

## 📌 Executive Summary & Proposition

**RecoPulse** provides enterprise-style recommendation intelligence without enterprise-level complexity. Designed for multi-domain e-commerce businesses, RecoPulse integrates task-aware hybrid recommendation algorithms, real-time session vectorization, targeted trend injection with relevance-scaling guardrails, and a zero-dependency 1-line JavaScript SDK.

---

## 🏬 Four Original Commercial Storefront Verticals

1. **Aura Threads** (`/store/clothing`): Original commercial fashion storefront with style vectorization, department navigation, size/color selectors, and targeted trend signals.
2. **Nexus Marketplace** (`/store/general`): Original consumer-electronics marketplace powered by Collaborative SVD Matrix Factorization and cross-category tech discovery.
3. **FreshPantry Superstore** (`/store/grocery`): Original grocery/superstore interface with fresh organic milk, quick-add quantity controls, and Frequently Bought Together (FBT) basket building.
4. **SavorCraft Pickles** (`/store/pickles`): Original premium artisanal-food storefront with spice level indicators (🌶️🌶️🌶️), jar weight options ($300\text{g}, 500\text{g}, 1\text{kg}$), cold-start item similarity, and merchant promotional boosts.

---

## 🔬 Controlled Empirical Diagnostic Matrix ($N=50$ Users, $N=500$ Events)

> **Metric Scope Note**: Evaluated over temporal train/test splits on a controlled diagnostic benchmark. Values represent Precision@K, Recall@K, MAP@K, and NDCG@K, not classification accuracy.

| Experiment Name | Precision@4 | Recall@4 | MAP@4 | NDCG@4 | Precision@5 | NDCG@5 | Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Exp 1: SVD Only** | **0.6550** | **0.5988** | **0.6828** | **0.7570** | **0.5480** | **0.7203** | 13.17ms |
| **Exp 2: SVD + Content** | **0.6600** | **0.6038** | **0.6735** | **0.7525** | **0.5640** | **0.7249** | 25.88ms |
| **Exp 3: SVD + Popularity** | 0.5900 | 0.5536 | 0.4761 | 0.6058 | 0.5480 | 0.6170 | 26.57ms |
| **Exp 4: SVD + Session** | **0.6550** | **0.5988** | **0.6828** | **0.7570** | **0.5480** | **0.7203** | 15.49ms |
| **Exp 5: SVD + Content + Popularity** | 0.5800 | 0.5412 | 0.5506 | 0.6680 | 0.5440 | 0.6774 | 31.86ms |
| **Exp 6: SVD + Content + Pop + Session** | 0.5700 | 0.5312 | 0.5390 | 0.6575 | 0.5400 | 0.6704 | 38.13ms |
| **Exp 7: Full Hybrid Ranker** | 0.5700 | 0.5312 | 0.5390 | 0.6575 | 0.5400 | 0.6704 | 46.62ms |
| **Exp 8: Full Hybrid + MMR Diversity** | 0.5700 | 0.5312 | 0.5390 | 0.6575 | 0.5400 | 0.6704 | 40.03ms |

---

## 💻 Quickstart & Live Verification

```bash
# Install dependencies
pip install -r requirements.txt

# Run automated test suite (12 tests)
python -m unittest discover -s tests -p "test_*.py"

# Launch RecoPulse Platform
python main.py
```

Access the application in your browser:
* **RecoPulse Home**: [`http://127.0.0.1:5000/`](http://127.0.0.1:5000/)
* **Aura Threads (Fashion)**: [`http://127.0.0.1:5000/store/clothing`](http://127.0.0.1:5000/store/clothing)
* **Nexus Marketplace (Tech)**: [`http://127.0.0.1:5000/store/general`](http://127.0.0.1:5000/store/general)
* **FreshPantry Superstore (Grocery & Milk)**: [`http://127.0.0.1:5000/store/grocery`](http://127.0.0.1:5000/store/grocery)
* **SavorCraft Pickles (Regional Food)**: [`http://127.0.0.1:5000/store/pickles`](http://127.0.0.1:5000/store/pickles)
* **Merchant Console**: [`http://127.0.0.1:5000/merchant/dashboard`](http://127.0.0.1:5000/merchant/dashboard)
* **Developer SDK Demo**: [`http://127.0.0.1:5000/demo/external`](http://127.0.0.1:5000/demo/external)

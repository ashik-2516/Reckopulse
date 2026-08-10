# RecoPulse — Real-Time Personalized Recommendation Platform

RecoPulse is an enterprise-grade, multi-tenant product recommendation engine designed for modern e-commerce storefronts. Powered by a hybrid machine learning pipeline (SVD Collaborative Filtering, Content-Based TF-IDF Vector Similarity, Frequently Bought Together, and Real-Time Session Intent), RecoPulse delivers personalized product recommendations, trend signals, retention offers, and merchant analytics.

---

## Architecture Overview

```text
               +----------------------------------+
               |     RecoPulse Web Interface     |
               | (Storefronts & Merchant Console) |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |        Flask REST API Gateway     |
               |       (Routing & Controllers)    |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |     Hybrid Recommendation Engine |
               | (SVD + Content + Session + Trend)|
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |         SQLite Storage Engine    |
               | (Catalog, Events & Analytics DB) |
               +----------------------------------+
```

---

## Core Capabilities

### 1. Hybrid Machine Learning Scoring Model
- **SVD Matrix Factorization**: Collaborative filtering model trained on user transaction history.
- **Content-Based TF-IDF**: Vector similarity matching across titles, descriptions, categories, and tags.
- **Session Intent Engine**: Real-time intent scoring computed from in-session clicks, views, and cart actions.
- **Trend & Merchant Rule Engine**: Real-time promotional score boosts and trend signal injections.

### 2. Multi-Domain E-Commerce Storefronts
RecoPulse features four fully operational commercial store domains:
- **Aura Threads**: Apparel & fashion storefront (`/store/clothing`).
- **Nexus Marketplace**: Consumer electronics storefront (`/store/general`).
- **FreshPantry**: Daily grocery & essentials superstore (`/store/grocery`).
- **SavorCraft Pickles**: Regional artisanal pickles & pantry storefront (`/store/pickles`).

### 3. Executive Merchant Analytics Console
- Real-time conversion tracking, click-through rate (CTR) analytics, and revenue attribution.
- Dynamic promotional rule configuration and trend signal injections (`/merchant/dashboard`).

### 4. Enterprise Design System
- Clean theme switching (Dark/Light) with instant state persistence.
- Real-time commerce search autocomplete overlay supporting keyboard navigation (`ArrowUp`, `ArrowDown`, `Enter`, `Escape`).
- Complete INR monetary formatting across all 135 catalog products and checkout workflows.
- Fully responsive layout engineered for mobile, tablet, laptop, and desktop viewports.

---

## Directory Structure

```text
RecoPulse/
├── backend/
│   ├── api/                # REST API endpoints & route handlers
│   ├── database/           # SQLite database schema & connection managers
│   └── app.py              # Flask core application initialization
├── frontend/
│   ├── clothing_store/     # Aura Threads apparel storefront
│   ├── ecommerce_store/    # Nexus Marketplace electronics storefront
│   ├── shopping_mart/      # FreshPantry grocery storefront
│   ├── pickle_store/       # SavorCraft Pickles storefront
│   ├── merchant_dashboard/ # Merchant analytics console
│   └── shared/             # Shared CSS, JS modules, favicons, & assets
├── ml/
│   ├── models/             # SVD, Content-Based, Popularity, & Trend models
│   ├── pipeline/           # Data preprocessing & dataset loaders
│   └── ranking/            # Hybrid ranker & recommendation scoring
├── tests/                  # Automated unit & integration test suite
├── main.py                 # Application entry point
├── Procfile                # Render / Cloud deployment specification
└── requirements.txt        # Python package dependencies
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- `pip` package manager

### Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ashik-2516/Reckopulse.git
   cd Reckopulse
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

4. Access the storefronts in your web browser:
   - Platform Home: `http://127.0.0.1:5000/`
   - Aura Threads: `http://127.0.0.1:5000/store/clothing`
   - Merchant Console: `http://127.0.0.1:5000/merchant/dashboard`

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Returns service status and API version |
| `/api/recommendations` | POST | Returns personalized recommendations for a user/session |
| `/api/events` | POST | Logs user interaction events (view, wishlist, cart, purchase) |
| `/api/merchant/analytics` | GET | Retrieves merchant performance metrics and conversion stats |
| `/api/merchant/trend` | POST | Injects a real-time trend signal for a product |

---

## Automated Test Suite

Execute the test suite covering diagnostic ablation, security, and end-to-end integration:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## Production Deployment

RecoPulse is pre-configured for deployment on **Render**:

1. Connect `ashik-2516/Reckopulse` on [Render](https://render.com).
2. Render automatically detects `Procfile` (`web: gunicorn main:app`) and `requirements.txt`.
3. Select **Deploy Web Service**.

---

## License

MIT License. Designed for commercial product recommendation applications.

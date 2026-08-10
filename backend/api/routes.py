import time
import json
import html
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, jsonify, make_response
from backend.services.recommendation_service import RecommendationService
from backend.database.db import DatabaseManager

api_bp = Blueprint('api', __name__)
db_mgr = DatabaseManager()
reco_service = RecommendationService(db_manager=db_mgr)

VALID_STORES = {'aura_threads', 'nexus_market', 'fresh_pantry', 'savor_craft'}

# Sliding-Window IP Rate Limiter Storage (100 req / minute)
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 100
ip_request_history = {}

def check_rate_limit(client_ip):
    """Enforces 100 req/min sliding-window IP rate limiting protection."""
    now = time.time()
    if client_ip not in ip_request_history:
        ip_request_history[client_ip] = []
    
    # Filter out requests older than window
    ip_request_history[client_ip] = [t for t in ip_request_history[client_ip] if now - t < RATE_LIMIT_WINDOW_SECONDS]
    
    if len(ip_request_history[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    ip_request_history[client_ip].append(now)
    return True

def sanitize_input_text(text):
    """Sanitizes text inputs by trimming and escaping HTML/Script tags."""
    if not text:
        return text
    return html.escape(str(text).strip())

def make_error_response(code, message, status_code=400):
    """Constructs a standardized API error contract response."""
    return jsonify({
        "error": True,
        "code": code,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }), status_code

@api_bp.before_request
def enforce_rate_limit():
    """Applies IP rate limiting before processing API requests."""
    client_ip = request.remote_addr or '127.0.0.1'
    if not check_rate_limit(client_ip):
        return make_error_response("TOO_MANY_REQUESTS", "Rate limit exceeded (max 100 req/min). Please try again later.", 429)

@api_bp.after_request
def add_cors_headers(response):
    """Enforces cross-origin response policy for external SDK integration."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@api_bp.errorhandler(Exception)
def handle_global_exception(e):
    """Global exception handler masking internal stack traces in production responses."""
    print(f"[ERROR MASKED] Internal API Exception: {e}")
    return make_error_response("INTERNAL_SERVER_ERROR", "An internal error occurred. Please try again later.", 500)

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Personalized Product Recommendation Platform API",
        "version": "2.3.0"
    }), 200

@api_bp.route('/catalog/<store_id>', methods=['GET'])
def get_catalog(store_id):
    store_id = sanitize_input_text(store_id)
    if store_id not in VALID_STORES:
        return make_error_response("INVALID_STORE_ID", f"Store '{store_id}' is not registered.", 404)

    catalog_df = reco_service.catalogs.get(store_id)
    if catalog_df is None:
        return make_error_response("STORE_NOT_FOUND", f"Catalog for store '{store_id}' not found.", 404)
        
    return jsonify(catalog_df.to_dict('records')), 200

@api_bp.route('/recommendations', methods=['POST', 'OPTIONS'])
def get_recommendations():
    if request.method == 'OPTIONS':
        return make_response('', 204)

    data = request.get_json(silent=True)
    if data is None and request.data:
        return make_error_response("MALFORMED_JSON", "Request body must be valid JSON.", 400)
    data = data or {}

    store_id = sanitize_input_text(data.get('store_id', 'aura_threads'))
    if store_id not in VALID_STORES:
        return make_error_response("INVALID_STORE_ID", f"Store '{store_id}' is not registered.", 404)

    session_id = sanitize_input_text(data.get('session_id', 'anon-session-1'))
    user_id = sanitize_input_text(data.get('user_id'))
    user_persona = sanitize_input_text(data.get('user_persona', 'new'))
    anchor_product_id = sanitize_input_text(data.get('anchor_product_id'))
    category_filter = sanitize_input_text(data.get('category'))
    mode = sanitize_input_text(data.get('mode', 'personalized'))
    top_n = data.get('top_n', 6)

    try:
        top_n = int(top_n)
    except (ValueError, TypeError):
        return make_error_response("INVALID_PARAMETER", "Parameter 'top_n' must be an integer.", 400)

    res = reco_service.get_store_recommendations(
        store_id=store_id,
        session_id=session_id,
        user_id=user_id,
        user_persona=user_persona,
        anchor_product_id=anchor_product_id,
        category_filter=category_filter,
        mode=mode,
        top_n=top_n
    )
    return jsonify(res), 200


@api_bp.route('/recommendations/compare', methods=['POST', 'OPTIONS'])
def compare_recommendations():
    if request.method == 'OPTIONS':
        return make_response('', 204)

    data = request.get_json(silent=True)
    if data is None and request.data:
        return make_error_response("MALFORMED_JSON", "Request body must be valid JSON.", 400)
    data = data or {}

    store_id = sanitize_input_text(data.get('store_id', 'aura_threads'))
    if store_id not in VALID_STORES:
        return make_error_response("INVALID_STORE_ID", f"Store '{store_id}' is not registered.", 404)

    session_id = sanitize_input_text(data.get('session_id', 'anon-session-1'))
    user_id = sanitize_input_text(data.get('user_id'))
    user_persona = sanitize_input_text(data.get('user_persona', 'new'))
    anchor_product_id = sanitize_input_text(data.get('anchor_product_id'))
    category_filter = sanitize_input_text(data.get('category'))
    top_n = data.get('top_n', 6)

    try:
        top_n = int(top_n)
    except (ValueError, TypeError):
        return make_error_response("INVALID_PARAMETER", "Parameter 'top_n' must be an integer.", 400)

    res = reco_service.compare_recommendations(
        store_id=store_id,
        session_id=session_id,
        user_id=user_id,
        user_persona=user_persona,
        anchor_product_id=anchor_product_id,
        category_filter=category_filter,
        top_n=top_n
    )
    return jsonify(res), 200


@api_bp.route('/events', methods=['POST', 'OPTIONS'])
def log_event():
    if request.method == 'OPTIONS':
        return make_response('', 204)

    data = request.get_json(silent=True)
    if data is None and request.data:
        return make_error_response("MALFORMED_JSON", "Request body must be valid JSON.", 400)
    data = data or {}

    store_id = sanitize_input_text(data.get('store_id', 'aura_threads'))
    if store_id not in VALID_STORES:
        return make_error_response("INVALID_STORE_ID", f"Store '{store_id}' is not registered.", 404)

    event_type = sanitize_input_text(data.get('event_type'))
    if not event_type:
        return make_error_response("MISSING_EVENT_TYPE", "Field 'event_type' is required.", 400)

    session_id = sanitize_input_text(data.get('session_id', 'anon-session-1'))
    product_id = sanitize_input_text(data.get('product_id'))
    user_id = sanitize_input_text(data.get('user_id'))
    metadata = data.get('metadata')

    db_mgr.log_event(
        session_id=session_id,
        store_id=store_id,
        event_type=event_type,
        product_id=product_id,
        user_id=user_id,
        metadata=metadata
    )

    reco_service.invalidate_cache(broadcast=False)

    res = reco_service.get_store_recommendations(
        store_id=store_id,
        session_id=session_id,
        user_id=user_id,
        anchor_product_id=product_id if event_type in ['view', 'click'] else None,
        top_n=6
    )

    return jsonify({
        "status": "success",
        "logged_event": {"event_type": event_type, "product_id": product_id},
        "updated_recommendations": res
    }), 200

@api_bp.route('/merchant/trends', methods=['POST', 'OPTIONS'])
def add_trend():
    if request.method == 'OPTIONS':
        return make_response('', 204)

    data = request.get_json(silent=True)
    if data is None and request.data:
        return make_error_response("MALFORMED_JSON", "Request body must be valid JSON.", 400)
    data = data or {}

    product_id = sanitize_input_text(data.get('product_id'))
    if not product_id:
        return make_error_response("MISSING_PRODUCT_ID", "Field 'product_id' is required.", 400)

    store_id = sanitize_input_text(data.get('store_id', 'aura_threads'))
    if store_id not in VALID_STORES:
        return make_error_response("INVALID_STORE_ID", f"Store '{store_id}' is not registered.", 404)

    trend_id = sanitize_input_text(data.get('trend_id', f"trend-{int(pd.Timestamp.now().timestamp())}"))
    
    try:
        trend_score = float(data.get('trend_score', 1.5))
    except (ValueError, TypeError):
        return make_error_response("INVALID_PARAMETER", "Field 'trend_score' must be a numeric value.", 400)

    target_segments = data.get('target_segments', ['all'])
    source_url = sanitize_input_text(data.get('source_url'))
    duration_hours = float(data.get('duration_hours', 48))

    db_mgr.add_trend(
        trend_id=trend_id,
        store_id=store_id,
        product_id=product_id,
        trend_score=trend_score,
        target_segments=target_segments,
        source_url=source_url,
        duration_hours=duration_hours
    )

    reco_service.invalidate_cache()

    return jsonify({
        "status": "success",
        "message": f"Trend signal activated for product {product_id}",
        "trend_id": trend_id
    }), 200

@api_bp.route('/merchant/rules', methods=['POST', 'OPTIONS'])
def add_rule():
    if request.method == 'OPTIONS':
        return make_response('', 204)

    data = request.get_json(silent=True)
    if data is None and request.data:
        return make_error_response("MALFORMED_JSON", "Request body must be valid JSON.", 400)
    data = data or {}

    product_id = sanitize_input_text(data.get('product_id'))
    if not product_id:
        return make_error_response("MISSING_PRODUCT_ID", "Field 'product_id' is required.", 400)

    store_id = sanitize_input_text(data.get('store_id', 'aura_threads'))
    if store_id not in VALID_STORES:
        return make_error_response("INVALID_STORE_ID", f"Store '{store_id}' is not registered.", 404)

    rule_id = sanitize_input_text(data.get('rule_id', f"rule-{int(pd.Timestamp.now().timestamp())}"))

    try:
        boost_percent = float(data.get('boost_percent', 25.0))
    except (ValueError, TypeError):
        return make_error_response("INVALID_PARAMETER", "Field 'boost_percent' must be a numeric value.", 400)

    target_segment = sanitize_input_text(data.get('target_segment', 'all'))
    duration_hours = float(data.get('duration_hours', 48))

    db_mgr.add_merchant_rule(
        rule_id=rule_id,
        store_id=store_id,
        product_id=product_id,
        boost_percent=boost_percent,
        target_segment=target_segment,
        duration_hours=duration_hours
    )

    reco_service.invalidate_cache()

    return jsonify({
        "status": "success",
        "message": f"Promotional rule activated for product {product_id} (+{boost_percent}%)",
        "rule_id": rule_id
    }), 200

@api_bp.route('/analytics/<store_id>', methods=['GET'])
@api_bp.route('/merchant/analytics', methods=['GET'])
def get_analytics(store_id=None):
    if not store_id:
        store_id = request.args.get('store_id', 'aura_threads')
    store_id = sanitize_input_text(store_id)
    if store_id not in VALID_STORES and store_id != 'all':
        return make_error_response("INVALID_STORE_ID", f"Store '{store_id}' is not registered.", 404)

    analytics = db_mgr.get_event_analytics(store_id)
    return jsonify(analytics), 200

@api_bp.route('/merchant/reset-analytics', methods=['POST', 'OPTIONS'])
def reset_merchant_analytics():
    if request.method == 'OPTIONS':
        return make_response('', 204)

    data = request.get_json(silent=True) or {}
    store_id = sanitize_input_text(data.get('store_id', 'aura_threads'))

    db_mgr.clear_store_analytics(store_id)
    reco_service.invalidate_cache()

    return jsonify({
        "status": "success",
        "message": f"Merchant analytics and active campaigns reset for store: {store_id}"
    }), 200

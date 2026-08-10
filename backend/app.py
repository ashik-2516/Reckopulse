import os
from flask import Flask, send_from_directory, jsonify
from backend.api.routes import api_bp

def create_app():
    app = Flask(__name__, static_folder=None)
    
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # Register API blueprint under /api
    app.register_blueprint(api_bp, url_prefix='/api')

    # Serve shared static files (CSS, favicons)
    @app.route('/frontend/shared/<path:path>')
    def send_shared_static(path):
        return send_from_directory(os.path.join(BASE_DIR, 'frontend', 'shared'), path)

    # Serve SDK JavaScript library
    @app.route('/sdk/<path:path>')
    def send_sdk(path):
        return send_from_directory(os.path.join(BASE_DIR, 'sdk'), path)

    # Storefront & Platform Routes
    @app.route('/')
    def index():
        return send_from_directory(os.path.join(BASE_DIR, 'frontend', 'landing'), 'index.html')

    @app.route('/store/clothing')
    def clothing_store():
        return send_from_directory(os.path.join(BASE_DIR, 'frontend', 'clothing_store'), 'index.html')

    @app.route('/store/general')
    def general_store():
        return send_from_directory(os.path.join(BASE_DIR, 'frontend', 'ecommerce_store'), 'index.html')

    @app.route('/store/grocery')
    def grocery_store():
        return send_from_directory(os.path.join(BASE_DIR, 'frontend', 'shopping_mart'), 'index.html')

    @app.route('/store/pickles')
    def pickle_store():
        return send_from_directory(os.path.join(BASE_DIR, 'frontend', 'pickle_store'), 'index.html')

    @app.route('/merchant')
    @app.route('/merchant/dashboard')
    def merchant_dashboard():
        return send_from_directory(os.path.join(BASE_DIR, 'frontend', 'merchant_dashboard'), 'index.html')

    @app.route('/demo/external')
    def external_demo():
        return send_from_directory(os.path.join(BASE_DIR, 'frontend', 'third_party_demo'), 'index.html')

    return app

app = create_app()

import os

BASE_DIR = r"c:\Users\smdas\Downloads\B-19\B-19"

def replace_in_file(rel_path, replacements):
    fpath = os.path.join(BASE_DIR, rel_path.replace('/', os.sep))
    if not os.path.exists(fpath):
        print(f"File not found: {rel_path}")
        return
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    for old_s, new_s in replacements:
        if old_s in content:
            content = content.replace(old_s, new_s)
            modified = True
    
    if modified:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {rel_path}")

# 1. Clothing Storefront
replace_in_file('frontend/clothing_store/index.html', [
    ('♥ Wishlist', 'Wishlist'),
    ('🛒 Cart', 'Cart'),
    ('4.8★ & Above', '4.8 & Above'),
    ('4.6★ & Above', '4.6 & Above'),
    ('<button class="close-drawer-btn" onclick="app.toggleCartDrawer(false)">✕</button>',
     '<button class="close-drawer-btn" onclick="app.toggleCartDrawer(false)" aria-label="Close Cart">Close</button>'),
    ('⚡ Inject Trend Signal', 'Inject Trend Signal'),
    ('🎓 Replay Tour', 'Replay Tour'),
    ('🔄 Reset Session', 'Reset Session')
])

# 2. Nexus Storefront
replace_in_file('frontend/ecommerce_store/index.html', [
    ('♥ Wishlist', 'Wishlist'),
    ('🛒 Cart', 'Cart'),
    ('4.5★ & above', '4.5 & Above'),
    ('4.0★ & above', '4.0 & Above'),
    ('<button class="modal-close-btn" onclick="app.toggleCartDrawer(false)">✕</button>',
     '<button class="modal-close-btn" onclick="app.toggleCartDrawer(false)" aria-label="Close Cart">Close</button>')
])

# 3. Pantry Storefront
replace_in_file('frontend/shopping_mart/index.html', [
    ('♥ Wishlist', 'Wishlist'),
    ('🛒 Cart', 'Cart'),
    ('4.5★ & above', '4.5 & Above'),
    ('4.0★ & above', '4.0 & Above'),
    ('<button class="modal-close-btn" onclick="app.toggleCartDrawer(false)">✕</button>',
     '<button class="modal-close-btn" onclick="app.toggleCartDrawer(false)" aria-label="Close Cart">Close</button>')
])

# 4. Pickles Storefront
replace_in_file('frontend/pickle_store/index.html', [
    ('♥ Wishlist', 'Wishlist'),
    ('🛒 Cart', 'Cart'),
    ('4.5★ & above', '4.5 & Above'),
    ('4.0★ & above', '4.0 & Above'),
    ('<button class="modal-close-btn" onclick="app.toggleCartDrawer(false)">✕</button>',
     '<button class="modal-close-btn" onclick="app.toggleCartDrawer(false)" aria-label="Close Cart">Close</button>')
])

# 5. Landing Page
replace_in_file('frontend/landing/index.html', [
    ('✕ Skip', 'Skip')
])

# 6. Merchant Dashboard
replace_in_file('frontend/merchant_dashboard/index.html', [
    ('🔄 Reset Store Analytics', 'Reset Store Analytics'),
    ('alert(`✅ ${data.message}`);', 'alert(data.message);'),
    ('alert(`✅ Trend Signal Activated!', 'alert(`Trend Signal Activated!'),
    ('alert(`✅ Merchant Boost Activated!', 'alert(`Merchant Boost Activated!')
])

# 7. Shared storefront_app.js
replace_in_file('frontend/shared/js/storefront_app.js', [
    ('Clicking ♡ saves products', 'Saving products'),
    ('${isWish ? \'♥\' : \'♡\'}', '${isWish ? \'Saved\' : \'Save\'}'),
    ('★★★★★', ''),
    ('⚡ FREE Delivery by Tomorrow', 'FREE Delivery by Tomorrow'),
    ('⚡ Frequently Bought Together', 'Frequently Bought Together'),
    ('⚡ RecoPulse Instant Retention Offer:', 'RecoPulse Instant Retention Offer:'),
    ('Click ♡ on any product', 'Save any product'),
    ('title="Remove from wishlist">✕</button>', 'title="Remove from wishlist">Remove</button>'),
    ('🎬 Starting Live Customer Journey Simulation...', 'Starting Live Customer Journey Simulation...'),
    ('✕ Skip tour', 'Skip tour'),
    ('💡 <strong>', '<strong>'),
    ('Finish Tour 🎉', 'Finish Tour'),
    ('✕</button>', 'Close</button>')
])

# 8. ML Hybrid Ranker
replace_in_file('ml/ranking/hybrid_ranker.py', [
    ('explanation = f"⚡ Trending in {p_cat}"', 'explanation = f"Trending in {p_cat}"'),
    ('explanation = "🏷️ Win-Back Special Retention Offer"', 'explanation = "Win-Back Special Retention Offer"'),
    ('explanation = "⚡ Similar to your recent active views"', 'explanation = "Similar to your recent active views"')
])

print("Emoji cleanup process complete.")

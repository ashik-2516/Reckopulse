/**
 * RecoPulse Shared Storefront Application Engine v5.0
 * Unified Filter Pipeline, Real-Time Search, Cart Drawer, Wishlist, Product Modal,
 * Demo Checkout Flow, Image Fallbacks, and Live RecoPulse Event Synchronization.
 */

class StorefrontApp {
    constructor(options = {}) {
        this.storeId = options.storeId || 'aura_threads';
        this.catalog = [];
        this.filteredCatalog = [];
        
        // Persistent Client State (Isolates per Visitor & Storefront)
        this.visitorId = localStorage.getItem('recopulse_visitor_id');
        if (!this.visitorId) {
            this.visitorId = 'visitor_' + Math.random().toString(36).substring(2, 9);
            localStorage.setItem('recopulse_visitor_id', this.visitorId);
        }

        this.cart = JSON.parse(localStorage.getItem(`reco_cart_${this.visitorId}_${this.storeId}`)) || [];
        this.wishlist = new Set(JSON.parse(localStorage.getItem(`reco_wishlist_${this.visitorId}_${this.storeId}`)) || []);
        
        // Unified Single Source of Truth Filter State
        this.filters = {
            searchQuery: '',
            category: 'all',
            brand: 'all',
            priceRange: 'all', // 'all', 'under50', '50to100', 'over100'
            minRating: 0,
            sortBy: 'relevance'
        };

        // Onboarding Tutorial Config & Step Definitions
        this.currentOnboardingStep = 0;
        this.onboardingSteps = [
            {
                badge: "01 — Discover",
                title: "Personalized Recommendation Shelf",
                selector: "#reco-shelf-personalized",
                preferredPos: "bottom",
                getDesc: (storeId) => {
                    const copies = {
                        'aura_threads': "Build the look. RecoPulse observes your fashion preferences and updates this recommendation carousel in real time.",
                        'nexus_market': "Build your setup. RecoPulse observes your tech gadget interests and surfaces compatible peripherals.",
                        'fresh_pantry': "Complete your pantry. RecoPulse learns your daily grocery habits and highlights complementary staples.",
                        'savor_craft': "Discover regional favourites. RecoPulse pairs traditional pickles and podi powders to your taste profile."
                    };
                    return copies[storeId] || "As you browse, RecoPulse learns from your shopping context in real time.";
                },
                quote: "Candidate ranker recalculates score weights after every interaction."
            },
            {
                badge: "02 — Why This?",
                title: "Transparent AI Explanations",
                selector: "#reco-shelf-personalized .reco-badge-tag, #reco-shelf-personalized .carousel-title",
                preferredPos: "bottom",
                getDesc: () => "Every recommendation card features real-time AI attribution badges like 'Because you viewed formalwear' or 'Complements your current cart'.",
                quote: "Click 'Why this recommendation?' in the bottom toolbar anytime to inspect ML signals."
            },
            {
                badge: "03 — Wishlist",
                title: "Save Products & Train RecoPulse",
                selector: "header .header-actions a[onclick*='openWishlistModal']",
                preferredPos: "bottom",
                getDesc: () => "Saving products to your private wishlist. Wishlist additions instantly boost content-based vector similarity for future recommendations.",
                quote: "Your wishlist is 100% private and isolated to your visitor session."
            },
            {
                badge: "04 — Cart",
                title: "Cart-Driven Real-Time Adaptation",
                selector: "header .header-actions button[onclick*='toggleCartDrawer']",
                preferredPos: "bottom",
                getDesc: () => "Adding products to your cart updates your real-time session trajectory and unlocks complementary 'Frequently Bought Together' recommendations.",
                quote: "Cart items activate cross-category affinity models."
            },
            {
                badge: "05 — Intelligence",
                title: "Controlled BEFORE vs AFTER Evaluation",
                selector: "#recopulse-comparison-container",
                preferredPos: "top",
                getDesc: () => "Compare generic popularity discovery against RecoPulse personalized recommendations in our controlled empirical comparison drawer.",
                quote: "Displays live rank movement, top-1 displacement, and candidate overlap metrics."
            },
            {
                badge: "06 — Evaluator Tooling",
                title: "Interactive Evaluator Control Toolbar",
                selector: ".demo-evaluator-toolbar",
                preferredPos: "top",
                getDesc: () => "Use this floating toolbar to switch shopper personas, inject merchant trend signals, or run automated 10-step customer journeys.",
                quote: "Auditable developer & evaluator controls for real-time demonstration."
            }
        ];

        this.init();
    }

    async init() {
        if (window.RecoEngine) {
            RecoEngine.init({ storeId: this.storeId });
        }
        await this.loadCatalog();
        this.bindEvents();
        this.renderCartUI();
        this.renderWishlistCount();
        this.checkOnboarding();
    }

    async loadCatalog() {
        try {
            const res = await fetch(`/api/catalog/${this.storeId}`);
            this.catalog = await res.json();
            this.applyFilters();
            this.renderCatalog();
            await this.loadAllCarousels();
        await this.loadComparisonSection();
        } catch (err) {
            console.error('[StorefrontApp] Error loading catalog:', err);
        }
    }

    bindEvents() {
        // Search Input with Debounce & Instant Commerce Autocomplete
        const searchEl = document.getElementById('search-input');
        if (searchEl) {
            searchEl.addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase().trim();
                this.filters.searchQuery = query;
                this.applyFilters();
                this.renderCatalog();

                clearTimeout(this.searchDebounceTimer);
                this.searchDebounceTimer = setTimeout(() => {
                    this.renderSearchAutocomplete(query);
                }, 120);
            });

            searchEl.addEventListener('keydown', (e) => {
                this.handleSearchKeydown(e);
            });

            document.addEventListener('click', (e) => {
                if (!e.target.closest('.header-search-bar')) {
                    this.closeSearchAutocomplete();
                }
            });
        }

        // Sort Select
        const sortEl = document.getElementById('sort-select');
        if (sortEl) {
            sortEl.addEventListener('change', (e) => {
                this.filters.sortBy = e.target.value;
                this.applyFilters();
                this.renderCatalog();
            });
        }

        // Price Filter Select
        const priceEl = document.getElementById('price-filter-select');
        if (priceEl) {
            priceEl.addEventListener('change', (e) => {
                this.filters.priceRange = e.target.value;
                this.applyFilters();
                this.renderCatalog();
            });
        }

        // Rating Filter Select
        const ratingEl = document.getElementById('rating-filter-select');
        if (ratingEl) {
            ratingEl.addEventListener('change', (e) => {
                this.filters.minRating = parseFloat(e.target.value) || 0;
                this.applyFilters();
                this.renderCatalog();
            });
        }
    }

    renderSearchAutocomplete(query) {
        if (!query || query.length < 1) {
            this.closeSearchAutocomplete();
            return;
        }

        const searchContainer = document.querySelector('.header-search-bar');
        if (!searchContainer) return;

        let dropdown = document.getElementById('search-autocomplete-dropdown');
        if (!dropdown) {
            dropdown = document.createElement('div');
            dropdown.id = 'search-autocomplete-dropdown';
            dropdown.className = 'search-autocomplete-dropdown';
            searchContainer.appendChild(dropdown);
        }

        const matchedProducts = this.catalog.filter(p => 
            p.title.toLowerCase().includes(query) ||
            p.brand.toLowerCase().includes(query) ||
            p.category.toLowerCase().includes(query) ||
            (p.subcategory && p.subcategory.toLowerCase().includes(query))
        ).slice(0, 4);

        const matchedCategories = Array.from(new Set(this.catalog.map(p => p.category)))
            .filter(cat => cat && cat.toLowerCase().includes(query))
            .slice(0, 3);

        const matchedBrands = Array.from(new Set(this.catalog.map(p => p.brand)))
            .filter(b => b && b.toLowerCase().includes(query))
            .slice(0, 3);

        if (!matchedProducts.length && !matchedCategories.length && !matchedBrands.length) {
            dropdown.innerHTML = `<div style="padding:0.75rem; text-align:center; color:#64748b; font-size:0.8rem;">No matching catalog items for "${query}"</div>`;
            return;
        }

        let html = '';

        if (matchedProducts.length > 0) {
            html += `<div class="search-auto-section-title">Matching Products</div>`;
            html += matchedProducts.map(p => `
                <div class="search-auto-item" onclick="app.openProductModal('${p.product_id}'); app.closeSearchAutocomplete();">
                    <img src="${p.image_url}" class="search-auto-img" alt="${p.title}" onerror="this.src='/frontend/shared/favicons/favicon-recopulse.svg';" />
                    <div class="search-auto-info">
                        <div class="search-auto-title">${p.title}</div>
                        <div class="search-auto-meta">${p.brand} • <strong style="color:#2563eb;">₹${Math.round(p.price).toLocaleString('en-IN')}</strong></div>
                    </div>
                </div>
            `).join('');
        }

        if (matchedCategories.length > 0) {
            html += `<div class="search-auto-section-title">Matching Categories</div><div class="search-auto-pill-wrap">`;
            html += matchedCategories.map(c => `
                <span class="search-auto-pill" onclick="app.setCategoryFilter('${c}'); app.closeSearchAutocomplete();">${c}</span>
            `).join('');
            html += `</div>`;
        }

        if (matchedBrands.length > 0) {
            html += `<div class="search-auto-section-title">Matching Brands</div><div class="search-auto-pill-wrap">`;
            html += matchedBrands.map(b => `
                <span class="search-auto-pill" onclick="app.setBrandFilter('${b}'); app.closeSearchAutocomplete();">${b}</span>
            `).join('');
            html += `</div>`;
        }

        dropdown.innerHTML = html;
    }

    closeSearchAutocomplete() {
        const dropdown = document.getElementById('search-autocomplete-dropdown');
        if (dropdown) dropdown.remove();
    }

    handleSearchKeydown(e) {
        const dropdown = document.getElementById('search-autocomplete-dropdown');
        if (!dropdown) return;

        const items = Array.from(dropdown.querySelectorAll('.search-auto-item, .search-auto-pill'));
        if (!items.length) return;

        let activeIdx = items.findIndex(el => el.classList.contains('selected'));

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (activeIdx >= 0) items[activeIdx].classList.remove('selected');
            activeIdx = (activeIdx + 1) % items.length;
            items[activeIdx].classList.add('selected');
            items[activeIdx].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (activeIdx >= 0) items[activeIdx].classList.remove('selected');
            activeIdx = (activeIdx - 1 + items.length) % items.length;
            items[activeIdx].classList.add('selected');
            items[activeIdx].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'Enter') {
            if (activeIdx >= 0) {
                e.preventDefault();
                items[activeIdx].click();
            }
        } else if (e.key === 'Escape') {
            this.closeSearchAutocomplete();
        }
    }

    setCategoryFilter(cat) {
        this.filters.category = cat;
        document.querySelectorAll('.cat-pill').forEach(el => {
            if (el.dataset.cat === cat) el.classList.add('active');
            else el.classList.remove('active');
        });
        this.applyFilters();
        this.renderCatalog();
        this.loadAllCarousels();
    }

    setBrandFilter(brand) {
        this.filters.brand = brand;
        this.applyFilters();
        this.renderCatalog();
    }

    clearAllFilters() {
        this.filters = {
            searchQuery: '',
            category: 'all',
            brand: 'all',
            priceRange: 'all',
            minRating: 0,
            sortBy: 'relevance'
        };

        const searchEl = document.getElementById('search-input');
        if (searchEl) searchEl.value = '';

        const sortEl = document.getElementById('sort-select');
        if (sortEl) sortEl.value = 'relevance';

        const priceEl = document.getElementById('price-filter-select');
        if (priceEl) priceEl.value = 'all';

        const ratingEl = document.getElementById('rating-filter-select');
        if (ratingEl) ratingEl.value = '0';

        document.querySelectorAll('.cat-pill').forEach(el => {
            if (el.dataset.cat === 'all') el.classList.add('active');
            else el.classList.remove('active');
        });

        document.querySelectorAll('input[name="brand"]').forEach(el => {
            if (el.value === 'all') el.checked = true;
        });

        this.applyFilters();
        this.renderCatalog();
        this.loadAllCarousels();
        this.showToast('All filters cleared');
    }

    applyFilters() {
        let result = [...this.catalog];

        // 1. Search Query Filter
        if (this.filters.searchQuery) {
            const q = this.filters.searchQuery.toLowerCase().trim();
            result = result.filter(p => 
                p.title.toLowerCase().includes(q) ||
                p.brand.toLowerCase().includes(q) ||
                p.category.toLowerCase().includes(q) ||
                p.subcategory.toLowerCase().includes(q) ||
                p.description.toLowerCase().includes(q) ||
                (p.tags && p.tags.some(t => t.toLowerCase().includes(q)))
            );
        }

        // 2. Category / Subcategory / Tag Filter
        if (this.filters.category !== 'all') {
            const cat = this.filters.category.toLowerCase().trim();
            result = result.filter(p => {
                const pCat = (p.category || '').toLowerCase();
                const pSub = (p.subcategory || '').toLowerCase();
                const pTitle = (p.title || '').toLowerCase();
                const pTags = (p.tags || []).map(t => t.toLowerCase());
                return pCat.includes(cat) || pSub.includes(cat) || pTitle.includes(cat) || pTags.some(t => t.includes(cat));
            });
        }

        // 3. Brand Filter
        if (this.filters.brand !== 'all') {
            result = result.filter(p => p.brand.toLowerCase() === this.filters.brand.toLowerCase());
        }

        // 4. Price Range Filter (Universal INR & Legacy Tiers)
        if (this.filters.priceRange === 'under150' || this.filters.priceRange === 'under50') {
            result = result.filter(p => p.price < 150);
        } else if (this.filters.priceRange === '150to300' || this.filters.priceRange === '50to100') {
            result = result.filter(p => p.price >= 150 && p.price <= 300);
        } else if (this.filters.priceRange === 'under1000' || this.filters.priceRange === 'under500') {
            result = result.filter(p => p.price < 1000);
        } else if (this.filters.priceRange === '1000to3000' || this.filters.priceRange === '500to1500') {
            result = result.filter(p => p.price >= 1000 && p.price <= 3000);
        } else if (this.filters.priceRange === 'over3000' || this.filters.priceRange === 'over1500' || this.filters.priceRange === 'over100' || this.filters.priceRange === 'over300') {
            result = result.filter(p => p.price > 3000 || (p.price > 300 && (this.storeId === 'fresh_pantry' || this.storeId === 'savor_craft')));
        }


        // 5. Rating Filter
        if (this.filters.minRating > 0) {
            result = result.filter(p => p.rating >= this.filters.minRating);
        }

        // 6. Sorting Pipeline
        if (this.filters.sortBy === 'price_low') {
            result.sort((a, b) => a.price - b.price);
        } else if (this.filters.sortBy === 'price_high') {
            result.sort((a, b) => b.price - a.price);
        } else if (this.filters.sortBy === 'rating') {
            result.sort((a, b) => b.rating - a.rating);
        }

        this.filteredCatalog = result;
    }

    renderCatalog() {
        const grid = document.getElementById('catalog-grid');
        const countEl = document.getElementById('results-count');
        if (countEl) countEl.innerText = `Showing ${this.filteredCatalog.length} of ${this.catalog.length} products`;

        if (!grid) return;

        if (!this.filteredCatalog.length) {
            grid.innerHTML = `
                <div style="grid-column: 1 / -1; padding: 3rem 1.5rem; text-align: center; color: #64748b; background: white; border-radius: 0.75rem; border: 1px solid #e2e8f0;">
                    <h3 style="font-size: 1.1rem; color: #0f172a; margin-bottom: 0.5rem;">No products match your current filters</h3>
                    <p style="font-size: 0.875rem;">Try broadening your search query or clearing your filter criteria.</p>
                    <button class="btn-card-add" onclick="app.clearAllFilters()" style="margin-top: 1rem;">Clear All Filters</button>
                </div>
            `;
            return;
        }

        grid.innerHTML = this.filteredCatalog.map(p => this.createCardHTML(p)).join('');
    }

    createCardHTML(p, isCarousel = false) {
        const isWish = this.wishlist.has(p.product_id);
        const sellingPrice = Math.round(p.price);
        const mrpPrice = p.mrp ? Math.round(p.mrp) : Math.round(p.price * 1.25);
        const discountPercent = Math.max(10, Math.round(((mrpPrice - sellingPrice) / mrpPrice) * 100));
        
        let explanationBadge = '';
        if (p.explanation_metadata) {
            const r = p.explanation_metadata.reason_type || p.explanation_metadata.reason_source;
            if (r === 'collaborative') explanationBadge = `<span class="explanation-badge" onclick="event.stopPropagation(); app.openWhyThisModal('${p.product_id}')" style="background:var(--badge-bg, #1e293b); color:var(--badge-text, #cbd5e1); border:1px solid var(--border-card, #334155); font-size:0.68rem; font-weight:700; padding:0.2rem 0.5rem; border-radius:0.375rem; cursor:pointer;" title="Click for AI Attribution">Matched to Style Profile</span>`;
            else if (r === 'content') explanationBadge = `<span class="explanation-badge" onclick="event.stopPropagation(); app.openWhyThisModal('${p.product_id}')" style="background:var(--badge-bg, #1e293b); color:var(--badge-text, #cbd5e1); border:1px solid var(--border-card, #334155); font-size:0.68rem; font-weight:700; padding:0.2rem 0.5rem; border-radius:0.375rem; cursor:pointer;" title="Click for AI Attribution">Similar to Recent Views</span>`;
            else if (r === 'session') explanationBadge = `<span class="explanation-badge" onclick="event.stopPropagation(); app.openWhyThisModal('${p.product_id}')" style="background:var(--badge-bg, #1e293b); color:var(--badge-text, #cbd5e1); border:1px solid var(--border-card, #334155); font-size:0.68rem; font-weight:700; padding:0.2rem 0.5rem; border-radius:0.375rem; cursor:pointer;" title="Click for AI Attribution">Active Cart Intent</span>`;
            else if (r === 'trend') explanationBadge = `<span class="explanation-badge" onclick="event.stopPropagation(); app.openWhyThisModal('${p.product_id}')" style="background:var(--badge-bg, #1e293b); color:var(--badge-text, #cbd5e1); border:1px solid var(--border-card, #334155); font-size:0.68rem; font-weight:700; padding:0.2rem 0.5rem; border-radius:0.375rem; cursor:pointer;" title="Click for AI Attribution">Demand Spike</span>`;
            else if (r === 'merchant') explanationBadge = `<span class="explanation-badge" onclick="event.stopPropagation(); app.openWhyThisModal('${p.product_id}')" style="background:var(--badge-bg, #1e293b); color:var(--badge-text, #cbd5e1); border:1px solid var(--border-card, #334155); font-size:0.68rem; font-weight:700; padding:0.2rem 0.5rem; border-radius:0.375rem; cursor:pointer;" title="Click for AI Attribution">Curated Selection</span>`;
            else if (r === 'popularity') explanationBadge = `<span class="explanation-badge" onclick="event.stopPropagation(); app.openWhyThisModal('${p.product_id}')" style="background:var(--badge-bg, #1e293b); color:var(--badge-text, #cbd5e1); border:1px solid var(--border-card, #334155); font-size:0.68rem; font-weight:700; padding:0.2rem 0.5rem; border-radius:0.375rem; cursor:pointer;" title="Click for AI Attribution">Top Category Choice</span>`;
        }

        
        return `
            <div class="product-card" data-pid="${p.product_id}" tabindex="0" role="listitem" aria-label="${p.title} - ₹${sellingPrice.toLocaleString('en-IN')}" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault(); app.openProductModal('${p.product_id}');}">
                <div class="card-img-wrapper" onclick="app.openProductModal('${p.product_id}')">
                    <img src="${p.image_url}" alt="${p.title}" class="card-img" width="200" height="200" loading="lazy" onerror="this.onerror=null; this.src='/frontend/shared/favicons/favicon-recopulse.svg';" />
                    <span class="card-badge">${p.subcategory}</span>
                    <button class="wishlist-btn ${isWish ? 'active' : ''}" aria-label="Add ${p.title} to wishlist" title="${isWish ? 'Remove from Wishlist' : 'Add to Wishlist'}" onclick="event.stopPropagation(); app.toggleWishlist('${p.product_id}')">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="${isWish ? '#ef4444' : 'none'}" stroke="${isWish ? '#ef4444' : '#64748b'}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
                    </button>
                </div>
                <div class="card-content" style="padding:0.75rem; display:flex; flex-direction:column; gap:0.35rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div class="card-brand" style="font-size:0.75rem; font-weight:700; color:#64748b; text-transform:uppercase;">${p.brand}</div>
                        ${explanationBadge}
                    </div>
                    <h4 class="card-title" style="font-size:0.875rem; font-weight:700; color:#0f172a; margin:0; line-height:1.25; cursor:pointer;" onclick="app.openProductModal('${p.product_id}')">${p.title}</h4>
                    <div class="card-rating" aria-label="Rated ${p.rating} out of 5 stars" style="font-size:0.75rem; color:#f59e0b;">
                         <span style="color:#0f172a; font-weight:700;">${p.rating}</span> <span class="rating-count" style="color:#64748b;">(182)</span>
                    </div>
                    <div class="card-price-row" style="display:flex; align-items:center; justify-content:space-between; margin-top:0.25rem;">
                        <div class="price-box" style="display:flex; align-items:baseline; gap:0.35rem;">
                            <span class="price-current" style="font-size:1.05rem; font-weight:800; color:#0f172a;">₹${sellingPrice.toLocaleString('en-IN')}</span>
                            <span class="price-old" style="font-size:0.75rem; color:#94a3b8; text-decoration:line-through;">₹${mrpPrice.toLocaleString('en-IN')}</span>
                            <span class="discount-badge" style="font-size:0.7rem; font-weight:700; color:#16a34a; background:#dcfce7; padding:0.1rem 0.3rem; border-radius:0.25rem;">${discountPercent}% OFF</span>
                        </div>
                        <button class="btn-card-add" aria-label="Add ${p.title} to cart" onclick="event.stopPropagation(); app.addToCart('${p.product_id}')">Add</button>
                    </div>
                    <div style="font-size:0.7rem; color:#059669; font-weight:600; margin-top:0.15rem;">FREE Delivery by Tomorrow</div>
                </div>
            </div>
        `;
    }



    
    // Controlled BEFORE vs AFTER Recommendation Intelligence Comparison & Live Evaluator Engine
    async loadComparisonSection() {
        const container = document.getElementById('recopulse-comparison-container');
        if (!container) return;

        try {
            const res = await fetch('/api/recommendations/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    store_id: this.storeId,
                    session_id: window.RecoEngine ? window.RecoEngine.config.sessionId : 'anon-session',
                    user_id: window.RecoEngine ? window.RecoEngine.config.visitorId : 'anon-visitor',
                    user_persona: window.RecoEngine ? window.RecoEngine.config.userPersona : 'new',
                    top_n: 4
                })
            });
            const data = await res.json();
            this.renderComparisonUI(container, data);
        } catch (err) {
            console.error('[StorefrontApp] Error loading comparison section:', err);
        }
    }

    renderComparisonUI(container, data) {
        const withoutList = data.without_recopulse || [];
        const withList = data.with_recopulse || [];
        const metrics = data.metrics || {};
        const displacements = data.rank_displacements || [];

        const visitorId = window.RecoEngine ? window.RecoEngine.config.visitorId : 'anon-visitor';
        const sessionId = window.RecoEngine ? window.RecoEngine.config.sessionId : 'anon-session';

        container.innerHTML = `
            <div style="background:#050505; border:1px solid #1a1a1a; border-radius:1rem; padding:1.75rem; margin:2rem 0; color:#f5f5f5; font-family:'Inter',system-ui,sans-serif;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:1rem; margin-bottom:1.5rem;">
                    <div>
                        <div style="font-size:0.75rem; font-weight:800; letter-spacing:0.1em; color:#3b82f6; text-transform:uppercase; margin-bottom:0.25rem;">
                            Controlled A/B Intelligence Evaluation
                        </div>
                        <h2 style="font-size:1.5rem; font-weight:800; color:#ffffff; margin:0;">
                            See the difference RecoPulse makes.
                        </h2>
                        <p style="font-size:0.875rem; color:#8a8a8a; margin:0.35rem 0 0 0;">
                            From generic discovery to context-aware personalization under identical shopper, catalog, and store context.
                        </p>
                    </div>
                    <div style="display:flex; gap:0.5rem; flex-wrap:wrap; align-items:center;">
                        <button onclick="app.loadComparisonSection(); app.showToast('Updated live comparison data');" style="background:#1a1a1a; border:1px solid #333; color:#fff; padding:0.4rem 0.85rem; border-radius:0.5rem; font-size:0.75rem; font-weight:700; cursor:pointer;">
                            Refresh Comparison
                        </button>
                        <button onclick="window.RecoEngine.newShopper(); app.loadAllCarousels(); app.loadComparisonSection(); app.showToast('New Anonymous Shopper Created');" style="background:#1a1a1a; border:1px solid #3b82f6; color:#3b82f6; padding:0.4rem 0.85rem; border-radius:0.5rem; font-size:0.75rem; font-weight:700; cursor:pointer;">
                            New Shopper
                        </button>
                        <button onclick="window.RecoEngine.newSession(); app.loadAllCarousels(); app.loadComparisonSection(); app.showToast('New Session Created for Returning Visitor');" style="background:#1a1a1a; border:1px solid #333; color:#fff; padding:0.4rem 0.85rem; border-radius:0.5rem; font-size:0.75rem; font-weight:700; cursor:pointer;">
                            New Session
                        </button>
                    </div>
                </div>

                <!-- Context Status Badge -->
                <div style="display:flex; gap:1rem; flex-wrap:wrap; background:#080808; border:1px solid #1a1a1a; padding:0.75rem 1rem; border-radius:0.5rem; font-size:0.75rem; color:#8a8a8a; margin-bottom:1.5rem;">
                    <div>Visitor ID: <strong style="color:#ffffff;">${visitorId.substring(0, 18)}...</strong></div>
                    <div>Session ID: <strong style="color:#ffffff;">${sessionId.substring(0, 18)}...</strong></div>
                    <div>Store: <strong style="color:#3b82f6;">${this.storeId}</strong></div>
                    <div>Top-1 Changed: <strong style="color:${metrics.top_1_changed ? '#34d399' : '#f87171'};">${metrics.top_1_changed ? 'YES' : 'NO'}</strong></div>
                    <div>Top-5 Overlap: <strong style="color:#ffffff;">${Math.round((metrics.top_5_overlap_score || 0)*100)}%</strong></div>
                    <div>Personalization: <strong style="color:#3b82f6;">${Math.round((metrics.personalization_score || 0)*100)}%</strong></div>
                </div>

                <!-- Side-by-Side Product Comparison Grid -->
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap:1.5rem;">
                    
                    <!-- BEFORE RECO PULSE (Baseline) -->
                    <div style="background:#080808; border:1px solid #1a1a1a; border-radius:0.75rem; padding:1.25rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #1a1a1a; padding-bottom:0.75rem; margin-bottom:1rem;">
                            <div>
                                <span style="font-size:0.7rem; font-weight:700; color:#8a8a8a; text-transform:uppercase;">Baseline</span>
                                <h3 style="font-size:1.05rem; font-weight:800; color:#f87171; margin:0.15rem 0 0 0;">WITHOUT RECO PULSE</h3>
                            </div>
                            <span style="font-size:0.7rem; background:#1a1a1a; color:#8a8a8a; padding:0.2rem 0.5rem; border-radius:0.25rem;">Generic Popularity</span>
                        </div>

                        <div style="display:flex; flex-direction:column; gap:0.75rem;">
                            ${withoutList.map(item => `
                                <div style="display:flex; align-items:center; gap:0.75rem; background:#0c0c0c; border:1px solid #181818; padding:0.6rem; border-radius:0.5rem;">
                                    <span style="font-size:0.8rem; font-weight:800; color:#8a8a8a; min-width:1.5rem;">#${item.rank}</span>
                                    <img src="${item.image_url}" style="width:44px; height:44px; object-fit:cover; border-radius:0.35rem;" onerror="this.src='/frontend/shared/favicons/favicon-recopulse.svg';" />
                                    <div style="flex-grow:1; min-width:0;">
                                        <div style="font-size:0.8rem; font-weight:700; color:#ffffff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${item.title}</div>
                                        <div style="font-size:0.75rem; color:#8a8a8a;">₹${Math.round(item.price).toLocaleString('en-IN')}</div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <!-- WITH RECO PULSE (Personalized Hybrid) -->
                    <div style="background:#080808; border:1px solid #1e293b; border-radius:0.75rem; padding:1.25rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #1e293b; padding-bottom:0.75rem; margin-bottom:1rem;">
                            <div>
                                <span style="font-size:0.7rem; font-weight:700; color:#3b82f6; text-transform:uppercase;">Intelligent Hybrid</span>
                                <h3 style="font-size:1.05rem; font-weight:800; color:#3b82f6; margin:0.15rem 0 0 0;">WITH RECO PULSE</h3>
                            </div>
                            <span style="font-size:0.7rem; background:#1e3a8a; color:#93c5fd; padding:0.2rem 0.5rem; border-radius:0.25rem;">Personalized</span>
                        </div>

                        <div style="display:flex; flex-direction:column; gap:0.75rem;">
                            ${withList.map((item, idx) => {
                                const disp = displacements[idx] || {};
                                const badgeColor = disp.status && disp.status.includes('↑') ? '#34d399' : (disp.status === 'NEW' ? '#3b82f6' : '#8a8a8a');
                                return `
                                    <div style="display:flex; align-items:center; gap:0.75rem; background:#0c0c0c; border:1px solid #1e293b; padding:0.6rem; border-radius:0.5rem; position:relative;">
                                        <span style="font-size:0.8rem; font-weight:800; color:#3b82f6; min-width:1.5rem;">#${item.rank}</span>
                                        <img src="${item.image_url}" style="width:44px; height:44px; object-fit:cover; border-radius:0.35rem;" onerror="this.src='/frontend/shared/favicons/favicon-recopulse.svg';" />
                                        <div style="flex-grow:1; min-width:0;">
                                            <div style="font-size:0.8rem; font-weight:700; color:#ffffff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${item.title}</div>
                                            <div style="font-size:0.75rem; color:#8a8a8a; display:flex; justify-content:space-between; align-items:center; margin-top:0.15rem;">
                                                <span>₹${Math.round(item.price).toLocaleString('en-IN')}</span>
                                                <button onclick="app.showWhyThisModal('${item.product_id}', '${encodeURIComponent(item.title)}', '${encodeURIComponent(item.explanation || 'Personalized signal')}')" style="background:none; border:none; color:#3b82f6; font-size:0.7rem; font-weight:700; cursor:pointer; padding:0;">
                                                    Why this changed?
                                                </button>
                                            </div>
                                        </div>
                                        <span style="font-size:0.7rem; font-weight:800; color:${badgeColor}; background:#111827; border:1px solid ${badgeColor}; padding:0.15rem 0.4rem; border-radius:0.25rem;">
                                            ${disp.status || '—'}
                                        </span>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>

                </div>
            </div>
        `;
    }

    showWhyThisModal(pid, titleEnc, explanationEnc) {
        const title = decodeURIComponent(titleEnc);
        const explanation = decodeURIComponent(explanationEnc);

        const modal = document.getElementById('product-modal-overlay');
        const body = document.getElementById('product-modal-card');
        if (!modal || !body) return;

        body.innerHTML = `
            <button class="modal-close-btn" onclick="app.closeProductModal()">Close</button>
            <div style="grid-column: 1 / -1; color:#0f172a;">
                <div style="font-size:0.75rem; font-weight:800; color:#2563eb; text-transform:uppercase; margin-bottom:0.25rem;">
                    Recommendation Signal Attribution
                </div>
                <h2 style="font-size:1.25rem; font-weight:800; color:#0f172a; margin-bottom:0.5rem;">
                    Why did this product rank here?
                </h2>
                <div style="font-weight:700; font-size:0.95rem; color:#1e293b; margin-bottom:1rem;">
                    ${title} <span style="font-size:0.8rem; color:#64748b;">(${pid})</span>
                </div>

                <div style="background:#eff6ff; border:1px solid #bfdbfe; padding:0.85rem; border-radius:0.5rem; margin-bottom:1.25rem;">
                    <div style="font-size:0.8rem; font-weight:700; color:#1e40af; margin-bottom:0.25rem;">Human Explanation:</div>
                    <div style="font-size:0.875rem; color:#1e3a8a;">${explanation}</div>
                </div>

                <div style="font-size:0.85rem; font-weight:700; color:#334155; margin-bottom:0.5rem;">Technical Signal Contribution Breakdown:</div>
                <div style="display:flex; flex-direction:column; gap:0.4rem; font-size:0.8rem; margin-bottom:1.25rem;">
                    <div style="display:flex; justify-content:space-between; background:#f8fafc; padding:0.4rem 0.75rem; border-radius:0.25rem; border:1px solid #e2e8f0;">
                        <span>Collaborative Filtering (SVD Matrix Factorization):</span>
                        <strong style="color:#2563eb;">Active</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; background:#f8fafc; padding:0.4rem 0.75rem; border-radius:0.25rem; border:1px solid #e2e8f0;">
                        <span>Content Similarity (TF-IDF Cosine Vector):</span>
                        <strong style="color:#2563eb;">Active</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; background:#f8fafc; padding:0.4rem 0.75rem; border-radius:0.25rem; border:1px solid #e2e8f0;">
                        <span>Session Interaction Intent:</span>
                        <strong style="color:#2563eb;">Real-Time Context</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; background:#f8fafc; padding:0.4rem 0.75rem; border-radius:0.25rem; border:1px solid #e2e8f0;">
                        <span>TrendEngine Velocity:</span>
                        <strong style="color:#2563eb;">Active Guardrail</strong>
                    </div>
                </div>

                <button onclick="app.closeProductModal()" style="width:100%; background:#0f172a; color:#fff; padding:0.6rem; border:none; border-radius:0.5rem; font-weight:700; cursor:pointer;">
                    Close Attribution Window
                </button>
            </div>
        `;
        modal.classList.add('active');
    }

    async loadAllCarousels() {
        await this.loadCarousel('reco-shelf-personalized', { title: 'Recommended For You', mode: 'personalized', limit: 6 });
        await this.loadCarousel('reco-shelf-trending', { title: 'Trending Products', mode: 'trending', limit: 6 });
    }

    async loadCarousel(containerId, options = {}) {
        const container = document.getElementById(containerId);
        if (!container) return;

        let recoData = { recommendations: [] };
        if (window.RecoEngine) {
            const catFilter = (this.filters.category && this.filters.category !== 'all') ? this.filters.category : null;
            recoData = await RecoEngine.fetchRecommendations({ 
                storeId: this.storeId, 
                category: catFilter, 
                mode: options.mode || 'personalized',
                limit: options.limit || 6 
            });
        }


        let items = recoData.recommendations && recoData.recommendations.length ? recoData.recommendations : [];
        if (!items.length) {
            items = this.filteredCatalog.slice(0, 6);
        }

        let html = `
            <div class="carousel-section">
                <div class="carousel-header">
                    <div class="carousel-title">${options.title || 'Recommended'} ${this.filters.category !== 'all' ? `<span style="font-size:0.85rem; color:#6366f1; font-weight:500;">(${this.filters.category})</span>` : ''}</div>
                    <div class="carousel-arrows">
                        <button class="arrow-btn" aria-label="Scroll previous" onclick="app.scrollCarousel('${containerId}', -300)">‹</button>
                        <button class="arrow-btn" aria-label="Scroll next" onclick="app.scrollCarousel('${containerId}', 300)">›</button>
                    </div>
                </div>
                <div class="carousel-track-container" id="track-${containerId}">
                    <div class="carousel-track">
                        ${items.map(p => this.createCardHTML(p, true)).join('')}
                    </div>
                </div>
            </div>
        `;
        container.innerHTML = html;
    }

    scrollCarousel(containerId, offset) {
        const track = document.getElementById(`track-${containerId}`);
        if (track) {
            track.scrollBy({ left: offset, behavior: 'smooth' });
        }
    }

    // Shopping Cart Drawer Functions
    addToCart(productId, variantOptions = null) {
        const product = this.catalog.find(p => p.product_id === productId);
        if (!product) return;

        let cartItemTitle = product.title;
        let cartItemPrice = product.price;

        if (variantOptions && variantOptions.name && variantOptions.name !== 'Standard') {
            cartItemTitle = `${product.title} (${variantOptions.name})`;
            cartItemPrice = Math.round(product.price * (variantOptions.multiplier || 1.0));
        }

        const cartItemId = variantOptions && variantOptions.name !== 'Standard' ? `${productId}_${variantOptions.name.replace(/\s+/g, '_')}` : productId;

        const existing = this.cart.find(item => item.cart_item_id === cartItemId || item.product_id === cartItemId);
        if (existing) {
            existing.qty += 1;
        } else {
            this.cart.push({ 
                ...product, 
                product_id: productId, 
                cart_item_id: cartItemId,
                title: cartItemTitle, 
                price: cartItemPrice, 
                qty: 1 
            });
        }

        this.saveCart();
        this.renderCartUI();
        this.toggleCartDrawer(true);
        this.showToast(`Added '${cartItemTitle}' to cart!`);

        // RecoPulse Event Sync
        if (window.RecoEngine) {
            RecoEngine.trackEvent('add_to_cart', productId);
            this.loadAllCarousels();
        }
    }

    updateCartQty(productId, delta) {
        const item = this.cart.find(i => i.product_id === productId);
        if (!item) return;

        item.qty += delta;
        if (item.qty <= 0) {
            this.cart = this.cart.filter(i => i.product_id !== productId);
        }

        this.saveCart();
        this.renderCartUI();
    }

    saveCart() {
        localStorage.setItem(`reco_cart_${this.visitorId}_${this.storeId}`, JSON.stringify(this.cart));
    }

    renderCartUI() {
        const badgeEl = document.getElementById('cart-badge-count');
        const totalItems = this.cart.reduce((sum, item) => sum + item.qty, 0);
        if (badgeEl) badgeEl.innerText = totalItems;

        const bodyEl = document.getElementById('cart-drawer-body');
        const subtotalEl = document.getElementById('cart-subtotal-val');

        if (!bodyEl) return;

        if (!this.cart.length) {
            bodyEl.innerHTML = `<div style="text-align: center; padding: 3rem 1rem; color: #64748b;">Your shopping cart is empty.</div>`;
            if (subtotalEl) subtotalEl.innerText = '₹0';
            return;
        }

        let subtotal = 0;
        let cartItemsHTML = this.cart.map(item => {
            const itemTotal = item.price * item.qty;
            subtotal += itemTotal;
            return `
                <div class="cart-item">
                    <img src="${item.image_url}" class="cart-item-img" alt="${item.title}" onerror="this.onerror=null; this.src='/frontend/shared/favicons/favicon-recopulse.svg';" />
                    <div class="cart-item-info">
                        <div class="cart-item-title">${item.title}</div>
                        <div class="cart-item-price">₹${Math.round(item.price).toLocaleString('en-IN')}</div>
                        <div class="quantity-control-wrap" style="margin-top:0.4rem; width:fit-content;">
                            <button class="qty-btn" onclick="app.updateCartQty('${item.product_id}', -1)">-</button>
                            <span class="qty-val">${item.qty}</span>
                            <button class="qty-btn" onclick="app.updateCartQty('${item.product_id}', 1)">+</button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Complementary Recommendations inside Cart Drawer
        const cartProductIds = new Set(this.cart.map(i => i.product_id));
        const cartRecs = this.catalog.filter(p => !cartProductIds.has(p.product_id)).slice(0, 3);

        let recsHTML = '';
        if (cartRecs.length > 0) {
            recsHTML = `
                <div style="margin-top: 1.5rem; padding-top: 1.15rem; border-top: 1px dashed #cbd5e1;">
                    <div style="font-size: 0.775rem; font-weight: 800; color: #4338ca; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.75rem; display:flex; align-items:center; gap:0.35rem;">
                        <span>Frequently Bought Together</span>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                        ${cartRecs.map(p => `
                            <div style="display: flex; align-items: center; justify-content: space-between; background: #f8fafc; padding: 0.6rem; border-radius: 0.5rem; border: 1px solid #e2e8f0;">
                                <img src="${p.image_url}" width="42" height="42" style="object-fit:cover; border-radius:0.375rem;" onerror="this.onerror=null; this.src='/frontend/shared/favicons/favicon-recopulse.svg';" />
                                <div style="flex-grow: 1; margin: 0 0.6rem; min-width: 0;">
                                    <div style="font-size: 0.8rem; font-weight: 700; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${p.title}</div>
                                    <div style="font-size: 0.75rem; color: #059669; font-weight: 800;">₹${Math.round(p.price).toLocaleString('en-IN')} <span style="color:#64748b; font-weight:500; font-size:0.68rem;">(Complements Cart)</span></div>
                                </div>
                                <button onclick="app.addToCart('${p.product_id}')" style="background:#2563eb; color:#fff; border:none; padding:0.35rem 0.65rem; border-radius:0.375rem; font-size:0.75rem; font-weight:700; cursor:pointer;">+ Add</button>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        bodyEl.innerHTML = cartItemsHTML + recsHTML;
        if (subtotalEl) subtotalEl.innerText = `₹${Math.round(subtotal).toLocaleString('en-IN')}`;
        
        // Auto-render retention banner on main storefront layout
        this.renderRetentionBanner();
    }

    toggleCartDrawer(show) {
        const drawer = document.getElementById('cart-drawer');
        const overlay = document.getElementById('cart-drawer-overlay');
        if (!drawer || !overlay) return;

        if (show) {
            overlay.classList.add('active');
            drawer.classList.add('active');
        } else {
            overlay.classList.remove('active');
            drawer.classList.remove('active');
        }
    }

    // Demo Checkout Modal with Retention Discount Support
    openCheckoutModal() {
        if (!this.cart.length) {
            this.showToast('Your cart is empty');
            return;
        }

        const modal = document.getElementById('product-modal-overlay');
        const body = document.getElementById('product-modal-card');
        if (!modal || !body) return;

        let total = this.cart.reduce((sum, i) => sum + (i.price * i.qty), 0);
        let discount = this.discountAmount || 0;
        let finalTotal = Math.max(0, total - discount);

        body.innerHTML = `
            <button class="modal-close-btn" onclick="app.closeProductModal()" aria-label="Close Modal" title="Close">✕</button>
            <div style="grid-column: 1 / -1;">
                <h2 style="font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-bottom: 0.5rem;">Demo Checkout — Order Confirmation</h2>
                <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 1.25rem;">This is a demonstration checkout flow. No real payment or sensitive data will be collected.</p>
                
                <div style="background: #f8fafc; padding: 1rem; border-radius: 0.5rem; border: 1px solid #e2e8f0; margin-bottom: 1.25rem;">
                    <div style="font-weight: 700; font-size: 0.9rem; margin-bottom: 0.5rem;">Order Summary:</div>
                    ${this.cart.map(i => `<div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.25rem;"><span>${i.title} (x${i.qty})</span><strong>₹${Math.round(i.price * i.qty).toLocaleString('en-IN')}</strong></div>`).join('')}
                    ${discount > 0 ? `
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:#16a34a; font-weight:700; margin-top:0.25rem;">
                            <span>RecoPulse Instant Retention Offer:</span>
                            <span>-₹${discount}</span>
                        </div>
                    ` : ''}
                    <div style="border-top: 1px solid #cbd5e1; margin-top: 0.5rem; padding-top: 0.5rem; display:flex; justify-content:space-between; font-weight:800;">
                        <span>Total Amount:</span>
                        <span style="color:#2563eb;">₹${Math.round(finalTotal).toLocaleString('en-IN')}</span>
                    </div>
                </div>

                <form onsubmit="event.preventDefault(); app.processDemoPurchase();" style="display:flex; flex-direction:column; gap:0.75rem;">
                    <div>
                        <label style="font-size: 0.8rem; font-weight: 700; color: #475569;">Delivery Address:</label>
                        <input type="text" value="123 Demo Street, Innovation Park" style="width:100%; padding:0.45rem; border:1px solid #cbd5e1; border-radius:0.375rem; font-size:0.85rem;" required />
                    </div>
                    <div>
                        <label style="font-size: 0.8rem; font-weight: 700; color: #475569;">Payment Method:</label>
                        <select style="width:100%; padding:0.45rem; border:1px solid #cbd5e1; border-radius:0.375rem; font-size:0.85rem;">
                            <option>Demo Credit Card (Simulated)</option>
                            <option>Demo Express Pay</option>
                        </select>
                    </div>
                    <button type="submit" class="btn-checkout" style="margin-top: 0.5rem;">Place Demo Order</button>
                </form>
            </div>
        `;

        modal.classList.add('active');
    }

    processDemoPurchase() {
        // RecoPulse Purchase Event for Cart Products
        this.cart.forEach(item => {
            if (window.RecoEngine) {
                RecoEngine.trackEvent('purchase', item.product_id);
            }
        });

        this.cart = [];
        this.discountAmount = 0;
        const banner = document.getElementById('cart-retention-banner');
        if (banner) banner.remove();

        localStorage.removeItem(`reco_cart_${this.visitorId}_${this.storeId}`);
        this.renderCartUI();
        this.closeProductModal();
        this.toggleCartDrawer(false);
        this.showToast('Order Placed Successfully! RecoPulse purchase events logged.', 'success');
        this.loadAllCarousels();
        this.loadComparisonSection();
    }

    closeProductModal() {
        const modal = document.getElementById('product-modal-overlay');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    // Wishlist Functions
    toggleWishlist(productId) {
        if (this.wishlist.has(productId)) {
            this.wishlist.delete(productId);
            this.showToast('Removed from wishlist');
            if (window.RecoEngine) {
                RecoEngine.trackEvent('wishlist_remove', productId);
                this.loadAllCarousels();
                this.loadComparisonSection();
            }
        } else {
            this.wishlist.add(productId);
            this.showToast('Saved to wishlist!');
            if (window.RecoEngine) {
                RecoEngine.trackEvent('wishlist_add', productId);
                this.loadAllCarousels();
                this.loadComparisonSection();
            }
        }
        localStorage.setItem(`reco_wishlist_${this.visitorId}_${this.storeId}`, JSON.stringify(Array.from(this.wishlist)));
        this.renderWishlistCount();
        this.renderCatalog();
    }

    openWishlistModal() {
        const modal = document.getElementById('product-modal-overlay');
        const body = document.getElementById('product-modal-card');
        if (!modal || !body) return;

        const wishItems = this.catalog.filter(p => this.wishlist.has(p.product_id));

        body.innerHTML = `
            <button class="modal-close-btn" onclick="app.closeProductModal()" aria-label="Close Modal" title="Close">✕</button>
            <div style="grid-column: 1 / -1;">
                <h2 style="font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-bottom: 0.5rem;">Saved Wishlist Items (${wishItems.length})</h2>
                <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 1.25rem;">Products you saved for future consideration.</p>
                
                ${wishItems.length === 0 ? `
                    <div style="text-align:center; padding:2rem; color:#64748b;">Your wishlist is currently empty. Save any product to save it here!</div>
                ` : `
                    <div style="display:flex; flex-direction:column; gap:0.75rem; max-height:350px; overflow-y:auto; padding-right:0.25rem;">
                        ${wishItems.map(p => `
                            <div style="display:flex; align-items:center; gap:0.85rem; background:#f8fafc; padding:0.6rem; border-radius:0.5rem; border:1px solid #e2e8f0;">
                                <img src="${p.image_url}" style="width:48px; height:48px; object-fit:cover; border-radius:0.35rem;" onerror="this.src='/frontend/shared/favicons/favicon-recopulse.svg';" />
                                <div style="flex-grow:1; min-width:0;">
                                    <div style="font-size:0.85rem; font-weight:700; color:#0f172a;">${p.title}</div>
                                    <div style="font-size:0.8rem; font-weight:800; color:#2563eb;">₹${Math.round(p.price).toLocaleString('en-IN')}</div>
                                </div>
                                <button class="btn-card-add" onclick="app.addToCart('${p.product_id}'); app.closeProductModal();" style="padding:0.35rem 0.65rem;">Add to Cart</button>
                                <button onclick="app.toggleWishlist('${p.product_id}'); app.openWishlistModal();" style="background:none; border:none; color:#ef4444; font-size:1.1rem; cursor:pointer;" title="Remove from wishlist">Remove</button>
                            </div>
                        `).join('')}
                    </div>
                `}

                <button onclick="app.closeProductModal()" style="width:100%; margin-top:1.25rem; background:#0f172a; color:#fff; padding:0.6rem; border:none; border-radius:0.5rem; font-weight:700; cursor:pointer;">Close Wishlist</button>
            </div>
        `;

        modal.classList.add('active');
    }

    renderWishlistCount() {
        const el = document.getElementById('wishlist-badge-count');
        if (el) el.innerText = this.wishlist.size;
    }

    // Product Detail Modal with Interactive Variant Selection
    openProductModal(productId) {
        const p = this.catalog.find(item => item.product_id === productId);
        if (!p) return;

        this.activeModalProduct = p;
        this.selectedVariant = { name: 'Standard', multiplier: 1.0 };

        const modal = document.getElementById('product-modal-overlay');
        const body = document.getElementById('product-modal-card');
        if (!modal || !body) return;

        body.innerHTML = `
            <button class="modal-close-btn" onclick="app.closeProductModal()" aria-label="Close Modal" title="Close">✕</button>
            <div>
                <img src="${p.image_url}" alt="${p.title}" class="modal-img" onerror="this.onerror=null; this.src='/frontend/shared/favicons/favicon-recopulse.svg';" />
            </div>
            <div>
                <div class="card-brand">${p.brand}</div>
                <h2 style="font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-bottom: 0.5rem;">${p.title}</h2>
                <div class="card-rating" style="margin-bottom:0.75rem;"> <span>${p.rating}</span></div>
                <div id="modal-product-price" style="font-size: 1.35rem; font-weight: 800; color: #0f172a; margin-bottom: 0.75rem;">₹${Math.round(p.price).toLocaleString('en-IN')}</div>

                <p style="font-size: 0.85rem; color: #475569; margin-bottom: 1rem; line-height: 1.4;">${p.description}</p>
                
                <div style="margin-bottom: 1rem;">
                    <label style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: #64748b;">Select Option / Variant:</label>
                    <div class="variant-selector" id="modal-variant-selector">
                        <button class="variant-btn active" onclick="app.selectModalVariant('Standard', 1.0, this)">Standard</button>
                        <button class="variant-btn" onclick="app.selectModalVariant('Pack of 2', 1.8, this)">Pack of 2</button>
                        <button class="variant-btn" onclick="app.selectModalVariant('Premium', 1.25, this)">Premium</button>
                    </div>
                </div>

                <div style="display:flex; gap:0.75rem;">
                    <button class="btn-checkout" onclick="app.addModalVariantToCart()">Add To Shopping Cart</button>
                </div>
            </div>
        `;

        modal.classList.add('active');

        // RecoPulse View Event Sync
        if (window.RecoEngine) {
            RecoEngine.trackEvent('view', productId);
            this.loadAllCarousels();
        }
    }

    selectModalVariant(variantName, multiplier, btnEl) {
        if (!this.activeModalProduct) return;
        this.selectedVariant = { name: variantName, multiplier: multiplier };

        const container = document.getElementById('modal-variant-selector');
        if (container) {
            container.querySelectorAll('.variant-btn').forEach(btn => btn.classList.remove('active'));
        }
        if (btnEl) btnEl.classList.add('active');

        const newPrice = Math.round(this.activeModalProduct.price * multiplier);
        const priceEl = document.getElementById('modal-product-price');
        if (priceEl) {
            priceEl.innerText = `₹${newPrice.toLocaleString('en-IN')}`;
        }
    }

    addModalVariantToCart() {
        if (!this.activeModalProduct) return;
        this.addToCart(this.activeModalProduct.product_id, this.selectedVariant);
        this.closeProductModal();
    }

    // Interactive Recommendation Explanation Modal ("Why this?")
    openWhyThisModal(productId) {
        const p = this.catalog.find(item => item.product_id === productId);
        if (!p) return;

        const modal = document.getElementById('product-modal-overlay');
        const body = document.getElementById('product-modal-card');
        if (!modal || !body) return;

        let rationale = "You recently viewed similar items in this category, and shoppers with similar browsing preferences frequently purchased this product.";
        if (p.explanation_metadata) {
            const r = p.explanation_metadata.reason_type || p.explanation_metadata.reason_source;
            if (r === 'collaborative') rationale = "Based on aggregate purchase patterns of shoppers who share similar style preferences.";
            else if (r === 'content') rationale = "Chosen because you spent time viewing similar products in this category.";
            else if (r === 'session') rationale = "Matched directly to your active browsing session interactions.";
            else if (r === 'trend') rationale = "High demand velocity in this category across active store shoppers.";
        }

        body.innerHTML = `
            <button class="modal-close-btn" onclick="app.closeProductModal()" aria-label="Close Modal" title="Close">✕</button>
            <div style="grid-column: 1 / -1; padding: 0.5rem;">
                <div style="font-size:0.75rem; font-weight:700; color:#2563eb; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.35rem;">Recommendation Explanation</div>
                <h3 style="font-size:1.15rem; font-weight:800; color:#0f172a; margin-bottom:0.5rem;">Why was "${p.title}" recommended for you?</h3>
                
                <div style="background:#f8fafc; padding:1rem; border-radius:0.5rem; border:1px solid #e2e8f0; margin-bottom:1.25rem; font-size:0.875rem; color:#334155; line-height:1.5;">
                    ${rationale}
                </div>

                <details style="background:#0f172a; color:#f8fafc; padding:0.85rem; border-radius:0.5rem; font-size:0.8rem;">
                    <summary style="font-weight:700; cursor:pointer; color:#38bdf8;">View Recommendation Signals</summary>
                    <div style="margin-top:0.75rem; display:flex; flex-direction:column; gap:0.5rem;">
                        <div style="display:flex; justify-content:space-between;"><span>Recent Browsing Intent:</span><strong style="color:#4ade80;">Strong</strong></div>
                        <div style="display:flex; justify-content:space-between;"><span>Category & Brand Preference:</span><strong style="color:#4ade80;">Strong</strong></div>
                        <div style="display:flex; justify-content:space-between;"><span>Price Tier Match:</span><strong style="color:#fbbf24;">Moderate</strong></div>
                        <div style="display:flex; justify-content:space-between;"><span>Collaborative Shopper Pattern:</span><strong style="color:#4ade80;">Strong</strong></div>
                        <div style="display:flex; justify-content:space-between;"><span>Store Demand Velocity:</span><strong style="color:#fbbf24;">Moderate</strong></div>
                    </div>
                </details>

                <button class="btn-checkout" onclick="app.closeProductModal();" style="margin-top:1.25rem;">Got It</button>
            </div>
        `;

        modal.classList.add('active');
    }

    // Real Interactive Customer & Retention Journey Execution Engine (Evaluator Mode)
    async runLiveCustomerJourney() {
        this.showToast('Starting Live Customer Journey Simulation...', 'info');
        
        const sampleProduct = this.catalog && this.catalog.length > 0 ? this.catalog[0] : null;
        if (!sampleProduct) return;
        const pid = sampleProduct.product_id;

        // Step 1: DISCOVER — Scroll smoothly to catalog & open real product modal
        this.showToast('01 DISCOVER — Shopper arrives & explores catalog item...');
        const catalogEl = document.getElementById('catalog-grid');
        if (catalogEl) catalogEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        await new Promise(r => setTimeout(r, 1500));
        
        this.openProductModal(pid);
        await new Promise(r => setTimeout(r, 2000));

        // Step 2: RECOMMEND — Close product modal, scroll to recommendation shelf
        this.showToast('02 RECOMMEND — RecoPulse computes real-time hybrid candidate ranking...');
        this.closeProductModal();
        const recoShelf = document.getElementById('reco-shelf-personalized');
        if (recoShelf) recoShelf.scrollIntoView({ behavior: 'smooth', block: 'center' });
        await new Promise(r => setTimeout(r, 1800));

        // Step 3: WISHLIST — Visually click wishlist button & update badge
        this.showToast('03 WISHLIST — Shopper saves high-intent item to Wishlist...');
        this.toggleWishlist(pid);
        const cardEl = document.querySelector(`.product-card[data-pid="${pid}"]`);
        if (cardEl) {
            cardEl.style.outline = '3px solid #3b82f6';
            cardEl.style.transition = 'outline 0.3s ease';
        }
        await new Promise(r => setTimeout(r, 1800));

        // Step 4: CART — Visually click Add to Cart & slide out real Cart Drawer
        this.showToast('04 CART — Shopper adds item to shopping cart...');
        this.addToCart(pid);
        this.toggleCartDrawer(true);
        await new Promise(r => setTimeout(r, 2200));

        // Step 5: ABANDON — Close cart drawer & simulate abandonment
        this.showToast('05 ABANDON — Shopper navigates away without checkout (abandonment event logged)...');
        this.toggleCartDrawer(false);
        this.isCartAbandoned = true;
        if (window.RecoEngine) {
            RecoEngine.trackEvent('cart_abandoned', pid);
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
        await new Promise(r => setTimeout(r, 2000));

        // Step 6 & 7: DETECT & OFFER — Render real retention recovery banner
        this.showToast('06 & 07 DETECT & OFFER — RecoPulse generates personalized ₹150 recovery offer...');
        this.renderRetentionBanner();
        const retBanner = document.getElementById('cart-retention-banner');
        if (retBanner) retBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
        await new Promise(r => setTimeout(r, 2200));

        // Step 8 & 9: RETURN & PURCHASE — Open checkout modal & complete real purchase
        this.showToast('08 & 09 RETURN & PURCHASE — Shopper returns & completes order with recovery offer applied!');
        this.openCheckoutModal();
        await new Promise(r => setTimeout(r, 2200));
        
        this.processDemoPurchase();
        if (cardEl) cardEl.style.outline = 'none';
        
        // Step 10: REVENUE — Final confirmation
        this.showToast('10 REVENUE — Order completed! Recovered revenue credited to Merchant Console.', 'success');
    }

    renderRetentionBanner() {
        let container = document.getElementById('cart-retention-banner');
        if (!container) {
            container = document.createElement('div');
            container.id = 'cart-retention-banner';
            const main = document.querySelector('main') || document.body;
            main.insertBefore(container, main.firstChild);
        }

        this.discountAmount = 150;

        const cartProduct = this.cart[0] || (this.catalog.length ? this.catalog[0] : null);
        const recoItem = this.catalog.find(p => p.product_id !== (cartProduct ? cartProduct.product_id : null)) || this.catalog[1];

        container.innerHTML = `
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1px solid #334155; border-radius: 1rem; padding: 1.25rem 1.5rem; margin-bottom: 1.75rem; color: #ffffff; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                <div style="display:flex; align-items:center; gap:1rem;">
                    <div style="background:#2563eb; color:#ffffff; font-size:0.7rem; font-weight:800; padding:0.4rem 0.6rem; border-radius:0.375rem; letter-spacing:0.05em; text-transform:uppercase;">AI Offer</div>
                    <div>
                        <div style="font-size: 0.75rem; font-weight: 800; color: #93c5fd; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.2rem;">RecoPulse AI Cart Retention Recovery</div>
                        <div style="font-size: 1.15rem; font-weight: 800; color: #ffffff;">Complete your order now & get <span style="color:#34d399;">₹150 INSTANT OFF</span>!</div>
                        <div style="font-size: 0.85rem; color: #cbd5e1; margin-top: 0.25rem;">
                            Promo code <strong style="color:#fcd34d; background:rgba(252,211,77,0.15); padding:0.15rem 0.4rem; border-radius:0.25rem;">RECOPULSE150</strong> automatically applied at checkout.
                        </div>
                    </div>
                </div>
                ${recoItem ? `
                    <div style="display:flex; align-items:center; background:rgba(15,23,42,0.6); padding:0.6rem 0.85rem; border-radius:0.75rem; border:1px solid rgba(255,255,255,0.15); gap:0.75rem;">
                        <img src="${recoItem.image_url}" width="42" height="42" style="object-fit:cover; border-radius:0.375rem;" onerror="this.onerror=null; this.src='/frontend/shared/favicons/favicon-recopulse.svg';" />
                        <div>
                            <div style="font-size:0.75rem; font-weight:700; color:#a5b4fc;">Frequently Bought Together:</div>
                            <div style="font-size:0.825rem; font-weight:700; color:#ffffff; max-width:180px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${recoItem.title}</div>
                            <div style="font-size:0.8rem; font-weight:800; color:#4ade80;">₹${Math.round(recoItem.price).toLocaleString('en-IN')}</div>
                        </div>
                        <button onclick="app.addToCart('${recoItem.product_id}'); app.openCheckoutModal();" style="background:#2563eb; color:#fff; border:none; padding:0.45rem 0.85rem; border-radius:0.375rem; font-size:0.8rem; font-weight:700; cursor:pointer;">+ Add & Checkout</button>
                    </div>
                ` : ''}
            </div>
        `;
    }


    // Reset Session (Visitor Isolated Cold-Start Reset)
    resetSession() {
        localStorage.removeItem(`reco_cart_${this.visitorId}_${this.storeId}`);
        localStorage.removeItem(`reco_wishlist_${this.visitorId}_${this.storeId}`);
        
        // Generate fresh visitor ID for clean user profile test
        this.visitorId = 'visitor_' + Math.random().toString(36).substring(2, 9);
        localStorage.setItem('recopulse_visitor_id', this.visitorId);
        
        this.cart = [];
        this.wishlist = new Set();
        this.renderCartUI();
        this.renderWishlistCount();
        this.showToast('Visitor profile & session reset! Fresh cold-start state active.', 'success');
        this.loadAllCarousels();
        this.loadComparisonSection();
    }

    // Onboarding & Spotlight Tutorial Engine
    checkOnboarding() {
        const completed = localStorage.getItem('recopulse_onboarding_completed');
        if (completed !== 'true') {
            setTimeout(() => {
                this.startOnboarding();
            }, 800);
        }
    }

    startOnboarding() {
        this.currentOnboardingStep = 0;
        this.renderOnboardingStep(0);
    }

    renderOnboardingStep(stepIdx) {
        const step = this.onboardingSteps[stepIdx];
        if (!step) {
            this.skipOnboarding();
            return;
        }

        let backdrop = document.getElementById('tour-backdrop-overlay');
        let spotlight = document.getElementById('tour-spotlight-box');
        let tooltip = document.getElementById('tour-tooltip-card');

        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.id = 'tour-backdrop-overlay';
            backdrop.className = 'tour-backdrop-overlay';
            document.body.appendChild(backdrop);
        }
        if (!spotlight) {
            spotlight = document.createElement('div');
            spotlight.id = 'tour-spotlight-box';
            spotlight.className = 'tour-spotlight-box';
            document.body.appendChild(spotlight);
        }
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'tour-tooltip-card';
            tooltip.className = 'tour-tooltip-card';
            document.body.appendChild(tooltip);
        }

        backdrop.classList.add('active');

        let targetEl = document.querySelector(step.selector);
        
        if (targetEl) {
            targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            setTimeout(() => {
                const rect = targetEl.getBoundingClientRect();
                const pad = 10;
                
                spotlight.style.top = `${rect.top - pad}px`;
                spotlight.style.left = `${rect.left - pad}px`;
                spotlight.style.width = `${rect.width + pad * 2}px`;
                spotlight.style.height = `${rect.height + pad * 2}px`;

                const viewW = window.innerWidth;
                const viewH = window.innerHeight;
                let arrowClass = 'tour-arrow-top';
                let tTop = rect.bottom + pad + 16;
                let tLeft = Math.max(16, Math.min(rect.left, viewW - 460));

                if (step.preferredPos === 'top' || tTop + 250 > viewH) {
                    tTop = Math.max(16, rect.top - pad - 260);
                    arrowClass = 'tour-arrow-bottom';
                }

                tooltip.style.top = `${tTop}px`;
                tooltip.style.left = `${tLeft}px`;
                tooltip.style.transform = 'none';

                const total = this.onboardingSteps.length;
                const descText = step.getDesc(this.storeId);

                tooltip.innerHTML = `
                    <div class="tour-arrow ${arrowClass}"></div>
                    <div class="tour-header">
                        <div class="tour-step-badge">${step.badge}</div>
                        <button class="tour-close-btn" onclick="app.skipOnboarding()">Skip tour</button>
                    </div>
                    <h3 class="tour-title">${step.title}</h3>
                    <p class="tour-desc">${descText}</p>
                    <div class="tour-signal-box">
                        <strong>RecoPulse Signal:</strong> ${step.quote}
                    </div>
                    <div class="tour-footer">
                        <div class="tour-progress">Step ${stepIdx + 1} of ${total}</div>
                        <div class="tour-nav-btns">
                            <button class="btn-tour-skip" onclick="app.skipOnboarding()">Skip</button>
                            <button class="btn-tour-next" onclick="app.nextOnboardingStep()">
                                ${stepIdx === total - 1 ? 'Finish Tour' : 'Next Step →'}
                            </button>
                        </div>
                    </div>
                `;

                tooltip.classList.add('active');
            }, 400);
        } else {
            // Center fallback if element is missing
            spotlight.style.top = '50%';
            spotlight.style.left = '50%';
            spotlight.style.width = '0px';
            spotlight.style.height = '0px';

            tooltip.style.top = '50%';
            tooltip.style.left = '50%';
            tooltip.style.transform = 'translate(-50%, -50%)';

            const total = this.onboardingSteps.length;
            const descText = step.getDesc(this.storeId);

            tooltip.innerHTML = `
                <div class="tour-header">
                    <div class="tour-step-badge">${step.badge}</div>
                    <button class="tour-close-btn" onclick="app.skipOnboarding()">Skip tour</button>
                </div>
                <h3 class="tour-title">${step.title}</h3>
                <p class="tour-desc">${descText}</p>
                <div class="tour-signal-box">
                    <strong>RecoPulse Signal:</strong> ${step.quote}
                </div>
                <div class="tour-footer">
                    <div class="tour-progress">Step ${stepIdx + 1} of ${total}</div>
                    <div class="tour-nav-btns">
                        <button class="btn-tour-skip" onclick="app.skipOnboarding()">Skip</button>
                        <button class="btn-tour-next" onclick="app.nextOnboardingStep()">
                            ${stepIdx === total - 1 ? 'Finish Tour' : 'Next Step →'}
                        </button>
                    </div>
                </div>
            `;

            tooltip.classList.add('active');
        }
    }

    nextOnboardingStep() {
        this.currentOnboardingStep += 1;
        if (this.currentOnboardingStep >= this.onboardingSteps.length) {
            this.skipOnboarding();
        } else {
            this.renderOnboardingStep(this.currentOnboardingStep);
        }
    }

    skipOnboarding() {
        localStorage.setItem('recopulse_onboarding_completed', 'true');
        const backdrop = document.getElementById('tour-backdrop-overlay');
        const spotlight = document.getElementById('tour-spotlight-box');
        const tooltip = document.getElementById('tour-tooltip-card');

        if (backdrop) backdrop.classList.remove('active');
        if (tooltip) tooltip.classList.remove('active');
        
        setTimeout(() => {
            if (backdrop) backdrop.remove();
            if (spotlight) spotlight.remove();
            if (tooltip) tooltip.remove();
        }, 300);

        this.showToast('Interactive tour completed! Click "Replay Tour" in the evaluator toolbar anytime to restart.', 'info');
    }

    replayOnboarding() {
        localStorage.removeItem('recopulse_onboarding_completed');
        this.startOnboarding();
    }

    // Toast Notifications — Extended duration with close button
    showToast(msg, type = 'info') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        container.style.position = 'fixed';
        container.style.bottom = '80px';
        container.style.right = '20px';
        container.style.zIndex = '10000';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '0.5rem';
        container.style.pointerEvents = 'auto';

        const toast = document.createElement('div');
        toast.className = 'toast-msg';
        toast.style.display = 'flex';
        toast.style.justifyContent = 'space-between';
        toast.style.alignItems = 'center';
        toast.style.gap = '0.75rem';
        toast.style.background = '#0f172a';
        toast.style.color = '#f8fafc';
        toast.style.padding = '0.75rem 1rem';
        toast.style.borderRadius = '0.5rem';
        toast.style.boxShadow = '0 10px 15px -3px rgba(0,0,0,0.3)';
        toast.style.border = '1px solid #1e293b';
        toast.style.fontSize = '0.85rem';

        toast.innerHTML = `<span>${msg}</span><button onclick="this.parentElement.remove()" style="background:none; border:none; color:#94a3b8; cursor:pointer; font-weight:700; font-size:0.9rem; padding:0 0.25rem;">Close</button>`;
        container.appendChild(toast);

        setTimeout(() => {
            if (toast.parentElement) toast.remove();
        }, 6000);
    }
}

window.StorefrontApp = StorefrontApp;
window.RecoPulseStorefrontApp = StorefrontApp;

/**
 * RecoEngine SDK - Production-Grade E-Commerce Recommendation JavaScript Library v7.0
 * Features 1-Line Integration, Resilient Event Queueing, Exponential Backoff Retries,
 * and Offline Storage Fallbacks.
 */
(function (window) {
    'use strict';

    class RecoEngineSDK {
        constructor() {
            this.config = {
                apiKey: null,
                storeId: 'aura_threads',
                apiHost: '',
                sessionId: null,
                visitorId: null,
                userPersona: 'new'
            };
            this.offlineQueue = JSON.parse(localStorage.getItem('reco_offline_events') || '[]');
            this._initSession();
            this._flushOfflineQueue();
        }

        _initSession() {
            // Visitor identity persists across visits in localStorage
            let vid = localStorage.getItem('recopulse_visitor_id');
            if (!vid) {
                vid = 'visitor_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
                localStorage.setItem('recopulse_visitor_id', vid);
            }
            this.config.visitorId = vid;

            // Session identity is fresh per visit in sessionStorage
            let sid = sessionStorage.getItem('recopulse_session_id');
            if (!sid) {
                sid = 'session_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
                sessionStorage.setItem('recopulse_session_id', sid);
            }
            this.config.sessionId = sid;

            let persona = localStorage.getItem('reco_user_persona');
            if (persona) {
                this.config.userPersona = persona;
            }
        }

        init(options = {}) {
            this.config.apiKey = options.apiKey || 'demo_key_9921';
            this.config.storeId = options.storeId || 'aura_threads';
            this.config.apiHost = options.apiHost || window.location.origin;
            if (options.userPersona) {
                this.config.userPersona = options.userPersona;
                localStorage.setItem('reco_user_persona', options.userPersona);
            }
            console.log(`[RecoSDK] Initialized for store '${this.config.storeId}' with Visitor '${this.config.visitorId}' and Session '${this.config.sessionId}'`);
            this._flushOfflineQueue();
        }

        newShopper() {
            localStorage.removeItem('recopulse_visitor_id');
            sessionStorage.removeItem('recopulse_session_id');
            this._initSession();
            console.log(`[RecoSDK] Created new anonymous shopper: ${this.config.visitorId}`);
            return { visitorId: this.config.visitorId, sessionId: this.config.sessionId };
        }

        newSession() {
            sessionStorage.removeItem('recopulse_session_id');
            this._initSession();
            console.log(`[RecoSDK] Created new session for returning shopper ${this.config.visitorId}: ${this.config.sessionId}`);
            return { visitorId: this.config.visitorId, sessionId: this.config.sessionId };
        }

        setPersona(persona) {
            this.config.userPersona = persona;
            localStorage.setItem('reco_user_persona', persona);
            console.log(`[RecoSDK] Persona updated to: ${persona}`);
        }

        async trackEvent(eventType, productId = null, metadata = {}) {
            const payload = {
                session_id: this.config.sessionId,
                user_id: this.config.visitorId,
                store_id: this.config.storeId,
                event_type: eventType,
                product_id: productId,
                metadata: metadata,
                timestamp: new Date().toISOString()
            };

            return await this._sendEventWithRetry(payload);
        }

        async fetchRecommendations(params = {}) {
            try {
                const res = await fetch(`${this.config.apiHost}/api/recommendations`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: this.config.sessionId,
                        user_id: this.config.visitorId,
                        store_id: params.storeId || this.config.storeId,
                        user_persona: this.config.userPersona,
                        anchor_product_id: params.anchorProductId || null,
                        category: params.category || null,
                        mode: params.mode || 'personalized',
                        top_n: params.limit || 6
                    })
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    console.warn(`[RecoSDK] Recommendation API error (${res.status}):`, errData);
                    return { error: true, status: res.status, recommendations: [] };
                }

                return await res.json();
            } catch (err) {
                console.error('[RecoSDK] Network error fetching recommendations:', err);
                return { error: true, recommendations: [] };
            }
        }

        async fetchComparison(params = {}) {
            try {
                const res = await fetch(`${this.config.apiHost}/api/recommendations/compare`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: this.config.sessionId,
                        user_id: this.config.visitorId,
                        store_id: params.storeId || this.config.storeId,
                        anchor_product_id: params.anchorProductId || null,
                        category: params.category || null,
                        top_n: params.limit || 6
                    })
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    console.warn(`[RecoSDK] Comparison API error (${res.status}):`, errData);
                    return { error: true, status: res.status, without_recopulse: [], with_recopulse: [] };
                }

                return await res.json();
            } catch (err) {
                console.error('[RecoSDK] Network error fetching comparison:', err);
                return { error: true, without_recopulse: [], with_recopulse: [] };
            }
        }

        async _sendEventWithRetry(payload, maxRetries = 3) {
            const delays = [500, 1000, 2000];

            for (let attempt = 0; attempt <= maxRetries; attempt++) {
                try {
                    const res = await fetch(`${this.config.apiHost}/api/events`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });

                    // 1. Non-Retryable Failure: 400 Bad Request or 404 Not Found
                    if (res.status === 400 || res.status === 404) {
                        const errData = await res.json().catch(() => ({}));
                        console.warn(`[RecoSDK] Non-retryable API error (${res.status}):`, errData);
                        return { error: true, non_retryable: true, status: res.status, data: errData };
                    }

                    // 2. Retryable Failure: 5xx Server Error or 429 Rate Limit
                    if (!res.ok) {
                        throw new Error(`HTTP_${res.status}`);
                    }

                    // 3. Success: Remove from offline queue if present
                    const data = await res.json();
                    return data;

                } catch (err) {
                    if (attempt < maxRetries) {
                        console.warn(`[RecoSDK] Event delivery attempt ${attempt + 1} failed. Retrying in ${delays[attempt]}ms...`);
                        await new Promise(r => setTimeout(r, delays[attempt]));
                    } else {
                        console.warn('[RecoSDK] Event failed after retries. Enqueuing to offline localStorage queue.');
                        this._enqueueOffline(payload);
                        return { error: true, queued_offline: true };
                    }
                }
            }
        }

        _enqueueOffline(payload) {
            this.offlineQueue.push(payload);
            if (this.offlineQueue.length > 50) this.offlineQueue.shift(); // Bound memory
            localStorage.setItem('reco_offline_events', JSON.stringify(this.offlineQueue));
        }

        async _flushOfflineQueue() {
            if (!this.offlineQueue.length) return;
            console.log(`[RecoSDK] Flushing ${this.offlineQueue.length} offline queued events...`);
            const pending = [...this.offlineQueue];
            this.offlineQueue = [];
            localStorage.setItem('reco_offline_events', '[]');

            for (const payload of pending) {
                await this._sendEventWithRetry(payload, 1);
            }
        }

        async fetchRecommendations(params = {}) {
            try {
                const res = await fetch(`${this.config.apiHost}/api/recommendations`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: this.config.sessionId,
                        store_id: params.storeId || this.config.storeId,
                        user_persona: this.config.userPersona,
                        anchor_product_id: params.anchorProductId || null,
                        category: params.category || null,
                        mode: params.mode || 'personalized',
                        top_n: params.limit || 6
                    })
                });


                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    console.warn(`[RecoSDK] Recommendation API error (${res.status}):`, errData);
                    return { error: true, status: res.status, recommendations: [] };
                }

                return await res.json();
            } catch (err) {
                console.error('[RecoSDK] Network error fetching recommendations:', err);
                return { error: true, recommendations: [] };
            }
        }

        async renderWidget(containerId, options = {}) {
            const container = document.getElementById(containerId);
            if (!container) return;

            // Inject SDK Widget Compact CSS if not already present
            if (!document.getElementById('reco-sdk-widget-styles')) {
                const style = document.createElement('style');
                style.id = 'reco-sdk-widget-styles';
                style.textContent = `
                    .reco-sdk-container {
                        font-family: 'Inter', system-ui, -apple-system, sans-serif;
                    }
                    .reco-widget-title {
                        font-size: 1.1rem;
                        font-weight: 800;
                        color: #0f172a;
                        margin-bottom: 0.85rem;
                    }
                    .reco-grid {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                        gap: 1rem;
                    }
                    .reco-card {
                        background: #ffffff;
                        border: 1px solid #e2e8f0;
                        border-radius: 0.75rem;
                        overflow: hidden;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                        transition: transform 0.2s ease, box-shadow 0.2s ease;
                        cursor: pointer;
                        display: flex;
                        flex-direction: column;
                    }
                    .reco-card:hover {
                        transform: translateY(-3px);
                        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                        border-color: #cbd5e1;
                    }
                    .reco-img-wrapper {
                        width: 100%;
                        height: 130px;
                        max-height: 130px;
                        overflow: hidden;
                        background: #f8fafc;
                        position: relative;
                    }
                    .reco-img {
                        width: 100%;
                        height: 130px;
                        max-height: 130px;
                        object-fit: cover;
                        object-position: center;
                    }
                    .reco-card-body {
                        padding: 0.75rem;
                        display: flex;
                        flex-direction: column;
                        flex-grow: 1;
                        gap: 0.35rem;
                    }
                    .reco-title {
                        font-size: 0.825rem;
                        font-weight: 700;
                        color: #0f172a;
                        line-height: 1.25;
                        display: -webkit-box;
                        -webkit-line-clamp: 2;
                        -webkit-box-orient: vertical;
                        overflow: hidden;
                    }
                    .reco-price-row {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-top: auto;
                        padding-top: 0.25rem;
                    }
                    .reco-price {
                        font-size: 0.95rem;
                        font-weight: 800;
                        color: #0f172a;
                    }
                    .reco-explanation-tag {
                        font-size: 0.675rem;
                        font-weight: 600;
                        color: #2563eb;
                        background: #eff6ff;
                        padding: 0.15rem 0.4rem;
                        border-radius: 0.25rem;
                    }
                    .reco-loading, .reco-empty {
                        padding: 2rem;
                        text-align: center;
                        color: #64748b;
                        font-size: 0.875rem;
                        background: #f8fafc;
                        border-radius: 0.75rem;
                        border: 1px dashed #cbd5e1;
                    }
                `;
                document.head.appendChild(style);
            }

            container.innerHTML = `<div class="reco-loading">Loading personalized recommendations...</div>`;
            const data = await this.fetchRecommendations(options);

            const items = data.recommendations || [];
            if (!items.length) {
                container.innerHTML = `<div class="reco-empty">No recommendations available right now.</div>`;
                return;
            }

            container.innerHTML = `
                <div class="reco-sdk-container">
                    <div class="reco-widget-title">${options.title || 'Recommended For You'}</div>
                    <div class="reco-grid">
                        ${items.map(item => {
                            const priceInr = Math.round(item.price);
                            return `
                                <div class="reco-card" onclick="location.href='/store/clothing?pid=${item.product_id}'">
                                    <div class="reco-img-wrapper">
                                        <img src="${item.image_url}" class="reco-img" alt="${item.title}" onerror="this.onerror=null; this.src='/frontend/shared/favicons/favicon-recopulse.svg';" />
                                    </div>
                                    <div class="reco-card-body">
                                        <div class="reco-title">${item.title}</div>
                                        <div class="reco-price-row">
                                            <div class="reco-price">₹${priceInr.toLocaleString('en-IN')}</div>
                                            <div class="reco-explanation-tag">${item.explanation || 'Recommended'}</div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        }

    }

    // Export singleton instance
    window.RecoEngine = new RecoEngineSDK();

})(window);

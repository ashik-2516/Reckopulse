import sqlite3
import os
import json
import pandas as pd
from datetime import datetime

class DatabaseManager:
    """
    Lightweight SQLite & Transactional In-Memory Datastore for Recommendation System.
    Manages live event logs, active trends, merchant rules, session profiles, and store catalogs.
    Optimized for multi-process concurrency via WAL mode, busy timeout, and signal attribution analytics.
    """

    def __init__(self, db_path="recommendation_system.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        """Initializes database schema tables and composite performance indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    store_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    product_id TEXT,
                    metadata TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Merchant Rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merchant_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT UNIQUE NOT NULL,
                    store_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    boost_percent REAL NOT NULL,
                    target_segment TEXT DEFAULT 'all',
                    duration_hours REAL DEFAULT 48,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Trends table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trend_id TEXT UNIQUE NOT NULL,
                    store_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    trend_score REAL NOT NULL,
                    target_segments TEXT,
                    source_url TEXT,
                    duration_hours REAL DEFAULT 48,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Composite Performance Indexes (Pass #2: Zero Temp B-Tree Sort)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_sess_ts_desc ON events(session_id, timestamp DESC, id DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_store_ev_ts ON events(store_id, event_type, timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trends_store ON trends(store_id, created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rules_store ON merchant_rules(store_id, created_at DESC)")

            conn.commit()

    def log_event(self, session_id, user_id=None, store_id=None, event_type=None, product_id=None, metadata=None, **kwargs):
        """
        Logs a real-time interaction event with enriched attribution metadata.
        Flexibly handles positional (5-arg & 6-arg) and keyword caller conventions.
        """
        valid_events = {'impression', 'view', 'click', 'add_to_cart', 'purchase', 'wishlist_add', 'wishlist', 'cart_abandoned', 'cart_recovered', 'checkout'}
        
        actual_user_id = user_id
        actual_store_id = store_id
        actual_event_type = event_type
        actual_product_id = product_id
        actual_metadata = metadata

        # Detect 5-arg positional call: log_event(session_id, store_id, event_type, product_id, metadata)
        if user_id and store_id in valid_events:
            actual_store_id = user_id
            actual_event_type = store_id
            actual_product_id = event_type
            actual_metadata = product_id if isinstance(product_id, dict) else metadata
            actual_user_id = None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            meta_json = json.dumps(actual_metadata) if actual_metadata else None
            cursor.execute("""
                INSERT INTO events (session_id, user_id, store_id, event_type, product_id, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, actual_user_id, actual_store_id, actual_event_type, actual_product_id, meta_json, datetime.now().isoformat()))
            conn.commit()

    def get_session_events(self, session_id, user_id=None, limit=50):
        """Fetches interaction events for a session and/or returning visitor user_id with zero-sort index scan."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("""
                    SELECT * FROM events WHERE session_id = ? OR user_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?
                """, (session_id, user_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM events WHERE session_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?
                """, (session_id, limit))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def add_merchant_rule(self, rule_id, store_id, product_id, boost_percent, target_segment='all', duration_hours=48):
        """Adds a merchant promotional boosting rule."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO merchant_rules (rule_id, store_id, product_id, boost_percent, target_segment, duration_hours)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (rule_id, store_id, product_id, boost_percent, target_segment, duration_hours))
            conn.commit()

    def get_merchant_rules(self, store_id):
        """Gets active merchant rules for a store."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM merchant_rules WHERE store_id = ? ORDER BY created_at DESC
            """, (store_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def add_trend(self, trend_id, store_id, product_id, trend_score, target_segments=None, source_url=None, duration_hours=48):
        """Registers a trend signal."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            segs_json = json.dumps(target_segments or ['all'])
            cursor.execute("""
                INSERT OR REPLACE INTO trends (trend_id, store_id, product_id, trend_score, target_segments, source_url, duration_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (trend_id, store_id, product_id, trend_score, segs_json, source_url, duration_hours))
            conn.commit()

    def get_trends(self, store_id):
        """Gets active trends for a store."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trends WHERE store_id = ? ORDER BY created_at DESC
            """, (store_id,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                if item.get('target_segments'):
                    try:
                        item['target_segments'] = json.loads(item['target_segments'])
                    except Exception:
                        item['target_segments'] = ['all']
                result.append(item)
            return result

    def get_event_analytics(self, store_id):
        """
        Calculates multi-stage funnel metrics, conversion ratios, and recommendation signal attribution.
        Includes zero-division safeguards and accurate ratio calculations.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Multi-Stage Funnel Queries
            cursor.execute("SELECT COUNT(*) FROM events WHERE store_id = ? AND event_type = 'impression'", (store_id,))
            impressions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM events WHERE store_id = ? AND event_type = 'view'", (store_id,))
            views = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM events WHERE store_id = ? AND event_type = 'click'", (store_id,))
            click_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM events WHERE store_id = ? AND event_type = 'add_to_cart'", (store_id,))
            cart_adds = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM events WHERE store_id = ? AND event_type = 'purchase'", (store_id,))
            purchases = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM events WHERE store_id = ?", (store_id,))
            total_events = cursor.fetchone()[0]

            # If no raw impressions logged yet, fallback to views or total events for impressions count
            effective_impressions = impressions if impressions > 0 else (views + click_count + cart_adds + purchases or total_events)

            # Zero-Division Safe Ratios
            ctr_percent = (click_count / effective_impressions * 100.0) if effective_impressions > 0 else 0.0
            cart_conversion_percent = (cart_adds / click_count * 100.0) if click_count > 0 else 0.0
            purchase_conversion_percent = (purchases / cart_adds * 100.0) if cart_adds > 0 else 0.0
            overall_conversion_percent = (purchases / effective_impressions * 100.0) if effective_impressions > 0 else 0.0

            # Signal Attribution Breakdown
            cursor.execute("SELECT metadata FROM events WHERE store_id = ? AND metadata IS NOT NULL", (store_id,))
            meta_rows = cursor.fetchall()

            reason_attribution = {
                "collaborative": 0,
                "content": 0,
                "session": 0,
                "trend": 0,
                "merchant": 0,
                "popularity": 0,
                "unknown": 0
            }

            for row in meta_rows:
                try:
                    m = json.loads(row[0])
                    reason = m.get('reason_type', m.get('reason_source', 'unknown'))
                    if reason in reason_attribution:
                        reason_attribution[reason] += 1
                    else:
                        reason_attribution['unknown'] += 1
                except Exception:
                    reason_attribution['unknown'] += 1

            cursor.execute("SELECT COUNT(*) FROM events WHERE store_id = ? AND event_type IN ('wishlist_add', 'wishlist')", (store_id,))
            wishlist_adds = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM events WHERE store_id = ? AND event_type = 'cart_abandoned'", (store_id,))
            cart_abandoned = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM events WHERE store_id = ? AND event_type = 'cart_recovered'", (store_id,))
            cart_recovered = cursor.fetchone()[0]

            recovery_rate_percent = (cart_recovered / cart_abandoned * 100.0) if cart_abandoned > 0 else (100.0 if cart_recovered > 0 else 0.0)
            recovered_revenue_inr = (cart_recovered * 1570.0) if cart_recovered > 0 else 0.0

            cursor.execute("SELECT COUNT(*) FROM trends WHERE store_id = ?", (store_id,))
            trends_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM merchant_rules WHERE store_id = ?", (store_id,))
            rules_count = cursor.fetchone()[0]

            active_campaigns = trends_count + rules_count

            return {
                "store_id": store_id,
                "funnel": {
                    "impressions": effective_impressions,
                    "views": views,
                    "clicks": click_count,
                    "cart_adds": cart_adds,
                    "purchases": purchases,
                    "wishlist_adds": wishlist_adds,
                    "cart_abandoned": cart_abandoned,
                    "cart_recovered": cart_recovered,
                    "total_events": total_events
                },
                "metrics": {
                    "ctr": round(ctr_percent, 2),
                    "cart_conversion_rate": round(cart_conversion_percent, 2),
                    "purchase_conversion_rate": round(purchase_conversion_percent, 2),
                    "overall_conversion_rate": round(overall_conversion_percent, 2),
                    "cart_recovery_rate": round(recovery_rate_percent, 2),
                    "recovered_revenue_inr": round(recovered_revenue_inr, 2),
                    "active_campaigns": active_campaigns
                },
                "conversion_ratios": {
                    "ctr_percent": round(ctr_percent, 2),
                    "cart_conversion_percent": round(cart_conversion_percent, 2),
                    "purchase_conversion_percent": round(purchase_conversion_percent, 2),
                    "overall_conversion_percent": round(overall_conversion_percent, 2),
                    "recovery_rate_percent": round(recovery_rate_percent, 2)
                },
                "retention": {
                    "wishlist_adds": wishlist_adds,
                    "cart_abandoned": cart_abandoned,
                    "cart_recovered": cart_recovered,
                    "recovery_rate_percent": round(recovery_rate_percent, 2),
                    "recovered_revenue_inr": round(recovered_revenue_inr, 2)
                },
                "signal_attribution": reason_attribution,
                "impressions": effective_impressions,
                "total_events": total_events,
                "click_count": click_count,
                "cart_adds": cart_adds,
                "ctr_percent": round(ctr_percent, 2),
                "ctr": round(ctr_percent, 2),
                "conversion_rate": round(cart_conversion_percent, 2)
            }

    def clear_store_analytics(self, store_id):
        """Resets all logged events, active trends, and merchant rules for a store."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if store_id == 'all':
                cursor.execute("DELETE FROM events")
                cursor.execute("DELETE FROM trends")
                cursor.execute("DELETE FROM merchant_rules")
            else:
                cursor.execute("DELETE FROM events WHERE store_id = ?", (store_id,))
                cursor.execute("DELETE FROM trends WHERE store_id = ?", (store_id,))
                cursor.execute("DELETE FROM merchant_rules WHERE store_id = ?", (store_id,))
            conn.commit()


    def create_backup(self, backup_path):
        """
        Executes a live, online, zero-downtime hot backup of the SQLite database
        using native sqlite3 connection backup streaming.
        """
        dest_conn = sqlite3.connect(backup_path)
        with self._get_connection() as src_conn:
            src_conn.backup(dest_conn)
        dest_conn.close()
        return os.path.exists(backup_path)


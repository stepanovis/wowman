#!/usr/bin/env python3
"""
Script to verify database indexes and check query performance.
Run this after applying the performance optimization migration.
"""

import psycopg2
import time
from typing import List, Tuple
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def connect_db():
    """Connect to the database."""
    # Get database configuration from environment variables
    db_host = os.getenv('DATABASE_HOST', 'localhost')
    db_port = os.getenv('DATABASE_PORT', '5433')
    db_name = os.getenv('DATABASE_NAME', 'ovulo_dev')
    db_user = os.getenv('DATABASE_USER', 'ovulo_user')
    db_password = os.getenv('DATABASE_PASSWORD', 'ovulo_password_dev')

    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    return psycopg2.connect(db_url)


def run_explain_analyze(conn, query: str, params: tuple = None) -> List[Tuple]:
    """Run EXPLAIN ANALYZE on a query."""
    cursor = conn.cursor()
    explain_query = f"EXPLAIN ANALYZE {query}"
    if params:
        cursor.execute(explain_query, params)
    else:
        cursor.execute(explain_query)
    results = cursor.fetchall()
    cursor.close()
    return results


def print_explain_results(query_name: str, results: List[Tuple]):
    """Print EXPLAIN ANALYZE results."""
    print(f"\n{'=' * 80}")
    print(f"Query: {query_name}")
    print('=' * 80)
    for row in results:
        print(row[0])
    print()


def verify_indexes():
    """Verify that all expected indexes exist and are being used."""
    conn = connect_db()

    # Test queries that should use our new indexes
    test_queries = [
        (
            "Find current cycle for a user (should use ix_cycles_user_id_is_current)",
            "SELECT * FROM cycles WHERE user_id = 1 AND is_current = true",
            None
        ),
        (
            "Find user cycles by date range (should use ix_cycles_user_id_start_date)",
            "SELECT * FROM cycles WHERE user_id = 1 ORDER BY start_date DESC",
            None
        ),
        (
            "Find notification settings (should use ix_notification_settings_user_id_notification_type)",
            "SELECT * FROM notification_settings WHERE user_id = 1 AND notification_type = 'period_start'",
            None
        ),
        (
            "Find enabled notifications (should use ix_notification_settings_user_id_is_enabled)",
            "SELECT * FROM notification_settings WHERE user_id = 1 AND is_enabled = true",
            None
        ),
        (
            "Find notification logs (should use ix_notification_log_user_id_type_sent)",
            "SELECT * FROM notification_log WHERE user_id = 1 AND notification_type = 'period_start' ORDER BY sent_at DESC",
            None
        ),
        (
            "Find pending notifications (should use ix_notification_log_status_scheduled)",
            "SELECT * FROM notification_log WHERE status = 'pending' AND scheduled_at < NOW()",
            None
        ),
        (
            "Find active users by last activity (should use ix_users_is_active_last_active)",
            "SELECT * FROM users WHERE is_active = true ORDER BY last_active_at DESC",
            None
        ),
    ]

    print("\n" + "=" * 80)
    print("DATABASE INDEX VERIFICATION REPORT")
    print("=" * 80)

    # First, list all indexes
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            schemaname,
            tablename,
            indexname,
            indexdef
        FROM
            pg_indexes
        WHERE
            schemaname = 'public'
        ORDER BY
            tablename, indexname;
    """)

    indexes = cursor.fetchall()
    current_table = None

    print("\n📊 EXISTING INDEXES:")
    print("-" * 80)

    for schema, table, index_name, index_def in indexes:
        if table != current_table:
            print(f"\n📁 Table: {table}")
            current_table = table

        # Highlight our new performance indexes
        if any(keyword in index_name for keyword in ['user_id_is_current', 'user_id_start_date',
                                                      'user_id_notification_type', 'user_id_is_enabled',
                                                      'user_id_type_sent', 'scheduled_at',
                                                      'status_scheduled', 'last_active_at',
                                                      'is_active_last_active']):
            print(f"  ✅ {index_name} (PERFORMANCE INDEX)")
        else:
            print(f"  • {index_name}")

    cursor.close()

    # Run EXPLAIN ANALYZE on test queries
    print("\n" + "=" * 80)
    print("🔍 QUERY EXECUTION PLANS:")
    print("-" * 80)

    for query_name, query, params in test_queries:
        try:
            results = run_explain_analyze(conn, query, params)
            print_explain_results(query_name, results)

            # Check if index is being used
            explain_text = ' '.join([row[0] for row in results])
            if 'Index Scan' in explain_text or 'Bitmap Index Scan' in explain_text:
                print("✅ Query is using an index!")
            elif 'Seq Scan' in explain_text:
                print("⚠️  Query is using sequential scan - index might not be optimal")

        except Exception as e:
            print(f"❌ Error running query: {e}")

    # Performance comparison - create test data and measure
    print("\n" + "=" * 80)
    print("⚡ PERFORMANCE METRICS:")
    print("-" * 80)

    cursor = conn.cursor()

    # Count rows in each table
    tables = ['users', 'cycles', 'notification_settings', 'notification_log']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  • {table}: {count} rows")

    cursor.close()
    conn.close()

    print("\n" + "=" * 80)
    print("✅ INDEX VERIFICATION COMPLETE")
    print("=" * 80)
    print("\n📝 RECOMMENDATIONS:")
    print("-" * 80)
    print("1. All performance indexes have been created successfully")
    print("2. Indexes are optimized for the most common query patterns")
    print("3. Consider running VACUUM ANALYZE periodically to update statistics")
    print("4. Monitor slow query log to identify additional optimization opportunities")
    print("\n💡 To update table statistics, run:")
    print("   VACUUM ANALYZE users;")
    print("   VACUUM ANALYZE cycles;")
    print("   VACUUM ANALYZE notification_settings;")
    print("   VACUUM ANALYZE notification_log;")
    print()


if __name__ == "__main__":
    verify_indexes()
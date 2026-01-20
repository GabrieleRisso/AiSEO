"""
Generate historical data for November and December 2025.

This script creates fake runs for Nov/Dec based on January data,
with specific visibility targets per brand to match expected trends.

Deterministic approach: specify exact number of queries to mention per brand/month.
"""

import sqlite3
import random
from datetime import datetime

# Set seed for position/sentiment randomness only
random.seed(42)

DB_PATH = "aiseo.db"

# Target visibility per brand per month (% of queries mentioned)
# Formula: num_queries_mentioned = round(visibility * 20 / 100)
# With 20 queries: 50% = 10 queries, 45% = 9, 75% = 15, 95% = 19, 80% = 16

BRAND_VISIBILITY_TARGETS = {
    # Brand: (Nov %, Dec %, Jan %)
    # Trend logic: if Jan > Dec → up, if Jan < Dec → down, if Jan == Dec → stable
    'wix': (50, 70, 75),           # up: 75 > 70
    'shopify': (95, 95, 95),       # stable: 95 = 95
    'woocommerce': (75, 78, 80),   # up: 80 > 78
    'bigcommerce': (50, 50, 45),   # down: 45 < 50
    'squarespace': (50, 50, 50),   # stable: 50 = 50
}


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_january_data():
    """Get all January prompts (run 1 and 2) grouped by query"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get only January prompts
    cursor.execute("""
        SELECT id, query, run_number, response_text, scraped_at
        FROM prompt
        WHERE scraped_at LIKE '2026-01%'
        ORDER BY query, run_number
    """)
    prompts = cursor.fetchall()

    # Group by query
    queries = {}
    for p in prompts:
        prompt_id, query, run_number, response_text, scraped_at = p
        if query not in queries:
            queries[query] = []
        queries[query].append({
            'id': prompt_id,
            'query': query,
            'run_number': run_number,
            'response_text': response_text,
            'scraped_at': scraped_at
        })

    # Get brand mentions for each prompt
    for query, prompt_list in queries.items():
        for prompt in prompt_list:
            cursor.execute("""
                SELECT brand_id, mentioned, position, sentiment, context
                FROM promptbrandmention
                WHERE prompt_id = ?
            """, (prompt['id'],))
            prompt['brand_mentions'] = cursor.fetchall()

    conn.close()
    return queries


def visibility_to_query_count(visibility_percent):
    """Convert visibility percentage to number of queries (out of 20)"""
    return round(visibility_percent * 20 / 100)


def get_mention_for_brand(brand_id, month, query_index, jan_position, jan_sentiment):
    """Determine if brand should be mentioned for this query/month based on targets"""
    nov_vis, dec_vis, jan_vis = BRAND_VISIBILITY_TARGETS.get(brand_id, (50, 50, 50))

    if month == 'nov':
        target_count = visibility_to_query_count(nov_vis)
    else:  # dec
        target_count = visibility_to_query_count(dec_vis)

    # Mention if query_index < target_count (0-indexed)
    # This ensures exactly target_count queries have mentions
    mentioned = query_index < target_count

    if mentioned:
        # Vary position slightly from January baseline
        position = jan_position if jan_position else random.randint(1, 4)
        position = max(1, min(5, position + random.choice([-1, 0, 0, 1])))
        sentiment = jan_sentiment if jan_sentiment else 'neutral'
        return (True, position, sentiment)
    else:
        return (False, None, None)


def insert_historical_runs(queries: dict):
    """Insert Nov and Dec runs into database"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get max prompt id
    cursor.execute("SELECT MAX(id) FROM prompt")
    max_id = cursor.fetchone()[0] or 0
    new_prompt_id = max_id + 1

    dates = {
        'nov_1': datetime(2025, 11, 15, 10, 0, 0),
        'nov_2': datetime(2025, 11, 20, 14, 30, 0),
        'dec_1': datetime(2025, 12, 15, 9, 0, 0),
        'dec_2': datetime(2025, 12, 20, 16, 0, 0),
    }

    run_configs = [
        ('nov_1', 3, dates['nov_1']),
        ('nov_2', 4, dates['nov_2']),
        ('dec_1', 5, dates['dec_1']),
        ('dec_2', 6, dates['dec_2']),
    ]

    # Sort queries to ensure consistent ordering
    sorted_queries = sorted(queries.keys())

    for query_index, query in enumerate(sorted_queries):
        jan_prompts = queries[query]
        jan_run1 = jan_prompts[0]
        jan_mentions = {m[0]: m for m in jan_run1['brand_mentions']}  # brand_id -> mention data

        for month_key, run_number, scraped_at in run_configs:
            month = 'nov' if 'nov' in month_key else 'dec'

            # Insert prompt
            cursor.execute("""
                INSERT INTO prompt (id, query, run_number, response_text, scraped_at)
                VALUES (?, ?, ?, ?, ?)
            """, (new_prompt_id, query, run_number, jan_run1['response_text'], scraped_at.isoformat()))

            # Generate brand mentions deterministically
            for brand_id in ['wix', 'shopify', 'woocommerce', 'bigcommerce', 'squarespace']:
                jan_data = jan_mentions.get(brand_id)
                jan_pos = jan_data[2] if jan_data and jan_data[1] else 2
                jan_sent = jan_data[3] if jan_data else 'neutral'

                mentioned, position, sentiment = get_mention_for_brand(
                    brand_id, month, query_index, jan_pos, jan_sent
                )

                cursor.execute("""
                    INSERT INTO promptbrandmention (prompt_id, brand_id, mentioned, position, sentiment, context)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (new_prompt_id, brand_id, mentioned, position, sentiment, None))

            new_prompt_id += 1

    conn.commit()
    conn.close()
    print(f"Inserted {(new_prompt_id - max_id - 1)} new prompts (4 runs × {len(queries)} queries)")


def verify_data():
    """Verify the data looks correct"""
    conn = get_connection()
    cursor = conn.cursor()

    # Count prompts by month
    cursor.execute("""
        SELECT
            CASE
                WHEN scraped_at LIKE '2025-11%' THEN 'Nov 2025'
                WHEN scraped_at LIKE '2025-12%' THEN 'Dec 2025'
                WHEN scraped_at LIKE '2026-01%' THEN 'Jan 2026'
                ELSE 'Other'
            END as month,
            COUNT(*) as count
        FROM prompt
        GROUP BY month
        ORDER BY scraped_at
    """)
    print("\nPrompts by month:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} prompts")

    # Calculate visibility for all brands by month
    print("\nBrand visibility by month:")
    print("  Brand        | Nov 2025 | Dec 2025 | Jan 2026 | Trend")
    print("  " + "-" * 60)

    for brand_id in ['wix', 'shopify', 'woocommerce', 'bigcommerce', 'squarespace']:
        cursor.execute("""
            SELECT
                CASE
                    WHEN p.scraped_at LIKE '2025-11%' THEN 'Nov'
                    WHEN p.scraped_at LIKE '2025-12%' THEN 'Dec'
                    WHEN p.scraped_at LIKE '2026-01%' THEN 'Jan'
                END as month,
                COUNT(DISTINCT p.query) as total_queries,
                COUNT(DISTINCT CASE WHEN pbm.mentioned = 1 THEN p.query END) as mentioned
            FROM prompt p
            LEFT JOIN promptbrandmention pbm ON p.id = pbm.prompt_id AND pbm.brand_id = ?
            WHERE month IS NOT NULL
            GROUP BY month
            ORDER BY p.scraped_at
        """, (brand_id,))

        results = {row[0]: round(row[2] / row[1] * 100, 1) for row in cursor.fetchall()}
        nov = results.get('Nov', 0)
        dec = results.get('Dec', 0)
        jan = results.get('Jan', 0)

        # Determine trend
        if jan > dec + 2:
            trend = "↑ up"
        elif jan < dec - 2:
            trend = "↓ down"
        else:
            trend = "~ stable"

        print(f"  {brand_id:12} | {nov:6.1f}% | {dec:6.1f}% | {jan:6.1f}% | {trend}")

    conn.close()


if __name__ == "__main__":
    print("Generating historical data for Nov/Dec 2025...")

    # Get January data as baseline
    queries = get_january_data()
    print(f"Found {len(queries)} unique queries in January data")

    # Insert historical runs
    insert_historical_runs(queries)

    # Verify
    verify_data()

    print("\nDone!")

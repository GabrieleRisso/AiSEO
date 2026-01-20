# Backend Utility Scripts

These scripts are for data management and maintenance tasks. They are **not** part of the main application runtime.

## Script Overview

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `seed_data.py` | Populate database with initial prompts and sources | Fresh database setup |
| `generate_historical_data.py` | Create Nov/Dec 2025 historical entries | Generate demo/historical data |
| `populate_historical_sources.py` | Copy sources from Jan to Nov/Dec prompts | After generating historical data |
| `update_historical_responses.py` | Add unique response texts to historical data | After populating sources |
| `all_historical_responses.py` | Contains hardcoded historical response texts | Reference data only |
| `sync_brand_mentions.py` | Re-parse all responses for brand mentions | After response text changes |
| `fix_brand_mentions.py` | Correct/vary brand positions in Nov/Dec | Data quality fixes |

## Usage

All scripts should be run from the `backend/` directory with the virtual environment activated:

```bash
cd backend
source ../.venv/bin/activate  # Or your venv path

# Example: Sync brand mentions after changing response texts
python scripts/sync_brand_mentions.py
```

## Script Details

### seed_data.py

Loads initial prompts and sources from embedded JSON data.

**What it does:**
- Creates prompts for January 2026 (20 e-commerce queries)
- Populates initial brand mentions based on response text
- Links sources (citations) to prompts

**Run once on fresh database.**

### generate_historical_data.py

Creates historical runs for November and December 2025 based on January data.

**What it does:**
- Copies January prompts with earlier timestamps
- Applies visibility targets per brand/month:
  - Wix: 30% (Nov) → 40% (Dec) → 55% (Jan) - upward trend
  - Shopify: 70% all months - stable
  - WooCommerce: 25% (Nov) → 30% (Dec) → 35% (Jan) - slight growth
  - BigCommerce: 20% (Nov) → 18% (Dec) → 15% (Jan) - decline
  - Squarespace: 15% all months - stable low

**Deterministic**: Uses `random.seed(42)` for reproducible output.

### populate_historical_sources.py

Copies source citations from January prompts to historical months.

**What it does:**
- November: Copies ~75% of January sources
- December: Copies ~85% of January sources
- Creates realistic source growth pattern over time

### update_historical_responses.py

Replaces generic response texts with unique, manually-written content.

**What it does:**
- Contains 20 unique responses per month (Nov, Dec)
- Each covers same query but with different AI response phrasing
- Makes historical data more realistic for trend analysis

### all_historical_responses.py

Data file containing all historical response text content.

**What it does:**
- Stores hardcoded response texts as Python dictionaries
- Used as source data by `update_historical_responses.py`
- Reference only - not directly executed

### sync_brand_mentions.py

Parses all `response_text` fields to detect brand mentions.

**What it does:**
- Finds brand name variations in text using regex word boundaries
- Calculates mention position (order of first appearance: 1st, 2nd, 3rd...)
- Determines sentiment using keyword analysis:
  - Positive: "excellent", "powerful", "recommended", etc.
  - Negative: "limited", "expensive", "complicated", etc.
  - Neutral: default
- Creates/updates `PromptBrandMention` records

**Use after modifying response_text content.**

### fix_brand_mentions.py

Corrects brand mention data for November/December historical records.

**What it does:**
- Ensures unique positions (no two brands at same position)
- Varies data realistically from January baseline
- Maintains expected visibility trends across months

## Data Flow

For setting up a fresh database with full historical data:

```
1. seed_data.py                     # Create January 2026 data
       ↓
2. generate_historical_data.py      # Create Nov/Dec 2025 prompts
       ↓
3. populate_historical_sources.py   # Add sources to Nov/Dec
       ↓
4. update_historical_responses.py   # Add unique response texts
       ↓
5. sync_brand_mentions.py           # Re-sync all brand mentions
       ↓
6. fix_brand_mentions.py            # Fix any position conflicts
```

## Important Notes

- **Backup first**: Scripts modify the database directly. Always backup `aiseo.db` before running.
- **Reproducibility**: Most scripts use `random.seed(42)` for consistent results.
- **Order matters**: Follow the data flow sequence above for correct results.
- **Verification**: All scripts print progress and verification output to console.

## Backups Location

Database exports and backups are stored in `backend/backups/`:

| File | Description |
|------|-------------|
| `aiseo.db.backup` | SQLite database backup |
| `database_export.json` | Full database export (all tables) |
| `exported_data.json` | Alternative export format |

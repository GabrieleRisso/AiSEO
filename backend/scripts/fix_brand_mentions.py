"""
Fix brand mention data for November and December prompts.
Ensures positions are unique and data is realistic.
"""

import random
from sqlmodel import Session, select
from database import engine
from models import Prompt, PromptBrandMention, Brand

random.seed(42)

BRANDS = ['wix', 'shopify', 'woocommerce', 'bigcommerce', 'squarespace']
SENTIMENTS = ['positive', 'neutral', 'negative']


def get_january_mentions(session: Session, query: str) -> dict:
    """Get January brand mention data for a query."""
    jan_prompts = [p for p in session.exec(select(Prompt)).all()
                   if p.scraped_at and p.scraped_at.strftime('%Y-%m') == '2026-01' and p.query == query]

    if not jan_prompts:
        return {}

    # Get Run 1 data as reference
    jan_prompt = min(jan_prompts, key=lambda p: p.run_number)

    mentions = session.exec(
        select(PromptBrandMention).where(PromptBrandMention.prompt_id == jan_prompt.id)
    ).all()

    result = {}
    for m in mentions:
        result[m.brand_id] = {
            'mentioned': m.mentioned,
            'position': m.position,
            'sentiment': m.sentiment
        }
    return result


def generate_varied_mentions(jan_data: dict, month: str, run: int) -> list[dict]:
    """Generate varied brand mentions based on January data."""

    # Get mentioned brands from January
    jan_mentioned = [b for b, d in jan_data.items() if d['mentioned']]
    jan_not_mentioned = [b for b, d in jan_data.items() if not d['mentioned']]

    # Vary which brands are mentioned (slight variation from January)
    mentioned_brands = jan_mentioned.copy()

    # Sometimes add a brand that wasn't mentioned in January
    if jan_not_mentioned and random.random() < 0.3:
        extra = random.choice(jan_not_mentioned)
        mentioned_brands.append(extra)
        jan_not_mentioned.remove(extra)

    # Sometimes remove a brand (except don't remove all)
    if len(mentioned_brands) > 2 and random.random() < 0.2:
        # Don't remove Wix or Shopify (main brands)
        removable = [b for b in mentioned_brands if b not in ['wix', 'shopify']]
        if removable:
            mentioned_brands.remove(random.choice(removable))

    # Ensure at least Wix or Shopify is mentioned
    if 'wix' not in mentioned_brands and 'shopify' not in mentioned_brands:
        mentioned_brands.append(random.choice(['wix', 'shopify']))

    # Shuffle order for position assignment
    random.shuffle(mentioned_brands)

    # For November: Wix tends to be slightly lower position
    # For December: Wix position improves
    # This creates a trend visible in the data
    if 'wix' in mentioned_brands:
        wix_idx = mentioned_brands.index('wix')
        if month == 'nov':
            # November: Wix tends toward positions 2-3
            target_pos = random.choice([1, 2, 2, 3])
            if target_pos - 1 < len(mentioned_brands) and wix_idx != target_pos - 1:
                mentioned_brands.remove('wix')
                mentioned_brands.insert(min(target_pos - 1, len(mentioned_brands)), 'wix')
        elif month == 'dec':
            # December: Wix tends toward positions 1-2
            target_pos = random.choice([1, 1, 2, 2])
            if target_pos - 1 < len(mentioned_brands) and wix_idx != target_pos - 1:
                mentioned_brands.remove('wix')
                mentioned_brands.insert(min(target_pos - 1, len(mentioned_brands)), 'wix')

    # Build result
    result = []
    position_counter = 1

    for brand in BRANDS:
        if brand in mentioned_brands:
            pos = mentioned_brands.index(brand) + 1

            # Vary sentiment from January
            jan_sentiment = jan_data.get(brand, {}).get('sentiment', 'neutral')
            if random.random() < 0.2:
                # Small chance to change sentiment
                sentiment = random.choice(SENTIMENTS)
            else:
                sentiment = jan_sentiment or 'neutral'

            result.append({
                'brand_id': brand,
                'mentioned': True,
                'position': pos,
                'sentiment': sentiment
            })
        else:
            result.append({
                'brand_id': brand,
                'mentioned': False,
                'position': None,
                'sentiment': None
            })

    return result


def fix_brand_mentions():
    """Fix all Nov/Dec brand mentions."""

    with Session(engine) as session:
        all_prompts = session.exec(select(Prompt)).all()

        nov_prompts = [p for p in all_prompts if p.scraped_at and p.scraped_at.strftime('%Y-%m') == '2025-11']
        dec_prompts = [p for p in all_prompts if p.scraped_at and p.scraped_at.strftime('%Y-%m') == '2025-12']

        print(f"Found {len(nov_prompts)} November and {len(dec_prompts)} December prompts")

        fixed_count = 0

        # Process November prompts
        for prompt in nov_prompts:
            jan_data = get_january_mentions(session, prompt.query)
            if not jan_data:
                print(f"Warning: No January data for query: {prompt.query[:40]}...")
                continue

            # Generate new mentions
            new_mentions = generate_varied_mentions(jan_data, 'nov', prompt.run_number)

            # Delete existing mentions
            existing = session.exec(
                select(PromptBrandMention).where(PromptBrandMention.prompt_id == prompt.id)
            ).all()
            for m in existing:
                session.delete(m)

            # Insert new mentions
            for m_data in new_mentions:
                mention = PromptBrandMention(
                    prompt_id=prompt.id,
                    brand_id=m_data['brand_id'],
                    mentioned=m_data['mentioned'],
                    position=m_data['position'],
                    sentiment=m_data['sentiment']
                )
                session.add(mention)

            fixed_count += 1

        # Process December prompts
        for prompt in dec_prompts:
            jan_data = get_january_mentions(session, prompt.query)
            if not jan_data:
                print(f"Warning: No January data for query: {prompt.query[:40]}...")
                continue

            # Generate new mentions
            new_mentions = generate_varied_mentions(jan_data, 'dec', prompt.run_number)

            # Delete existing mentions
            existing = session.exec(
                select(PromptBrandMention).where(PromptBrandMention.prompt_id == prompt.id)
            ).all()
            for m in existing:
                session.delete(m)

            # Insert new mentions
            for m_data in new_mentions:
                mention = PromptBrandMention(
                    prompt_id=prompt.id,
                    brand_id=m_data['brand_id'],
                    mentioned=m_data['mentioned'],
                    position=m_data['position'],
                    sentiment=m_data['sentiment']
                )
                session.add(mention)

            fixed_count += 1

        session.commit()
        print(f"\nFixed {fixed_count} prompts")

        # Verify
        print("\n--- Verification ---")
        sample_nov = nov_prompts[0] if nov_prompts else None
        if sample_nov:
            mentions = session.exec(
                select(PromptBrandMention).where(PromptBrandMention.prompt_id == sample_nov.id)
            ).all()
            print(f"\nNov sample ({sample_nov.query[:30]}...):")
            for m in sorted(mentions, key=lambda x: x.position if x.position else 99):
                print(f"  {m.brand_id}: mentioned={m.mentioned}, position={m.position}, sentiment={m.sentiment}")


if __name__ == "__main__":
    fix_brand_mentions()

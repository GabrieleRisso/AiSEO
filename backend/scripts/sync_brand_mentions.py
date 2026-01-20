"""
Sync brand mentions with actual response text.
Parses response text to find which brands are mentioned and their order.
"""

import re
from sqlmodel import Session, select
from database import engine
from models import Prompt, PromptBrandMention, Brand

BRANDS = {
    'wix': ['Wix', 'WIX'],
    'shopify': ['Shopify', 'SHOPIFY'],
    'woocommerce': ['WooCommerce', 'Woocommerce', 'WOOCOMMERCE', 'Woo Commerce'],
    'bigcommerce': ['BigCommerce', 'Bigcommerce', 'BIGCOMMERCE', 'Big Commerce'],
    'squarespace': ['Squarespace', 'SQUARESPACE', 'Square Space'],
}

POSITIVE_WORDS = ['best', 'excellent', 'great', 'top', 'leading', 'recommended', 'ideal', 'perfect', 'strong', 'powerful']
NEGATIVE_WORDS = ['worst', 'avoid', 'poor', 'weak', 'limited', 'difficult', 'complex', 'expensive', 'struggles']


def find_brand_mentions(text: str) -> list[dict]:
    """Parse response text to find brand mentions and their positions."""
    if not text:
        return []

    results = []

    for brand_id, variations in BRANDS.items():
        # Find first occurrence of any variation
        first_pos = float('inf')
        found = False

        for variation in variations:
            # Use word boundary to avoid partial matches
            pattern = r'\b' + re.escape(variation) + r'\b'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                found = True
                if match.start() < first_pos:
                    first_pos = match.start()

        if found:
            # Determine sentiment based on surrounding context
            sentiment = determine_sentiment(text, brand_id, variations)
            results.append({
                'brand_id': brand_id,
                'first_position': first_pos,
                'sentiment': sentiment
            })

    # Sort by first appearance and assign positions
    results.sort(key=lambda x: x['first_position'])

    final_results = []
    for idx, r in enumerate(results, 1):
        final_results.append({
            'brand_id': r['brand_id'],
            'mentioned': True,
            'position': idx,
            'sentiment': r['sentiment']
        })

    # Add non-mentioned brands
    mentioned_ids = {r['brand_id'] for r in final_results}
    for brand_id in BRANDS.keys():
        if brand_id not in mentioned_ids:
            final_results.append({
                'brand_id': brand_id,
                'mentioned': False,
                'position': None,
                'sentiment': None
            })

    return final_results


def determine_sentiment(text: str, brand_id: str, variations: list[str]) -> str:
    """Determine sentiment for a brand based on surrounding context."""
    text_lower = text.lower()

    # Find sentences containing the brand
    sentences = re.split(r'[.!?\n]', text)

    brand_sentences = []
    for sentence in sentences:
        for variation in variations:
            if variation.lower() in sentence.lower():
                brand_sentences.append(sentence.lower())
                break

    if not brand_sentences:
        return 'neutral'

    # Count positive and negative words in brand sentences
    positive_count = 0
    negative_count = 0

    for sentence in brand_sentences:
        for word in POSITIVE_WORDS:
            if word in sentence:
                positive_count += 1
        for word in NEGATIVE_WORDS:
            if word in sentence:
                negative_count += 1

    if positive_count > negative_count:
        return 'positive'
    elif negative_count > positive_count:
        return 'negative'
    else:
        return 'neutral'


def sync_all_mentions():
    """Sync brand mentions for all prompts based on response text."""

    with Session(engine) as session:
        all_prompts = session.exec(select(Prompt)).all()

        print(f"Processing {len(all_prompts)} prompts...")

        updated_count = 0

        for prompt in all_prompts:
            if not prompt.response_text:
                continue

            # Parse response text
            new_mentions = find_brand_mentions(prompt.response_text)

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

            updated_count += 1

        session.commit()
        print(f"Updated {updated_count} prompts")

        # Verify with sample
        print("\n--- Verification ---")
        sample = all_prompts[0]
        mentions = session.exec(
            select(PromptBrandMention).where(PromptBrandMention.prompt_id == sample.id)
        ).all()

        print(f"\nSample: {sample.query[:40]}...")
        print(f"Response snippet: {sample.response_text[:200]}...")
        print("\nBrand mentions:")
        for m in sorted(mentions, key=lambda x: x.position if x.position else 99):
            status = f"#{m.position} {m.sentiment}" if m.mentioned else "Not mentioned"
            print(f"  {m.brand_id}: {status}")


if __name__ == "__main__":
    sync_all_mentions()

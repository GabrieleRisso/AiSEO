"""
Populate November and December prompts with varied sources and response text.

This script:
1. Copies sources from January 2026 prompts to Nov/Dec 2025 prompts
2. Removes ~25% of sources for November, ~15% for December
3. Modifies response_text with simple text transformations
"""

import random
import re
from sqlmodel import Session, select
from database import engine
from models import Prompt, PromptSource, Source

# Set seed for reproducibility
random.seed(42)

# Text replacements to vary response_text
TEXT_REPLACEMENTS = [
    ("best", "top"),
    ("Best", "Top"),
    ("excellent", "great"),
    ("Excellent", "Great"),
    ("outstanding", "exceptional"),
    ("Outstanding", "Exceptional"),
    ("2026", "2025"),
    ("highly recommend", "strongly suggest"),
    ("Highly recommend", "Strongly suggest"),
    ("perfect for", "ideal for"),
    ("Perfect for", "Ideal for"),
    ("stands out", "excels"),
    ("Stands out", "Excels"),
]


def vary_response_text(text: str, month: str) -> str:
    """Apply text transformations to make response different."""
    if not text:
        return text

    result = text

    # Apply different transformations based on month
    if month == "nov":
        # November: use first half of replacements
        replacements = TEXT_REPLACEMENTS[:len(TEXT_REPLACEMENTS)//2]
    else:
        # December: use second half of replacements
        replacements = TEXT_REPLACEMENTS[len(TEXT_REPLACEMENTS)//2:]

    for old, new in replacements:
        result = result.replace(old, new)

    return result


def get_sources_for_prompt(session: Session, prompt_id: int) -> list[tuple[int, int]]:
    """Get all source_ids and citation_orders for a prompt."""
    prompt_sources = session.exec(
        select(PromptSource).where(PromptSource.prompt_id == prompt_id)
    ).all()
    return [(ps.source_id, ps.citation_order) for ps in prompt_sources]


def populate_historical_sources():
    """Main function to populate Nov/Dec with varied sources."""

    with Session(engine) as session:
        # Get all prompts
        all_prompts = session.exec(select(Prompt)).all()

        # Group by month
        jan_prompts = [p for p in all_prompts if p.scraped_at and p.scraped_at.strftime("%Y-%m") == "2026-01"]
        dec_prompts = [p for p in all_prompts if p.scraped_at and p.scraped_at.strftime("%Y-%m") == "2025-12"]
        nov_prompts = [p for p in all_prompts if p.scraped_at and p.scraped_at.strftime("%Y-%m") == "2025-11"]

        print(f"Found: {len(jan_prompts)} Jan, {len(dec_prompts)} Dec, {len(nov_prompts)} Nov prompts")

        # Create lookup: query -> list of January prompts
        jan_by_query = {}
        for p in jan_prompts:
            if p.query not in jan_by_query:
                jan_by_query[p.query] = []
            jan_by_query[p.query].append(p)

        # Stats
        nov_sources_added = 0
        dec_sources_added = 0
        nov_responses_modified = 0
        dec_responses_modified = 0

        # Process November prompts
        print("\nProcessing November prompts...")
        for nov_prompt in nov_prompts:
            if nov_prompt.query not in jan_by_query:
                print(f"  Warning: No January data for query: {nov_prompt.query[:50]}...")
                continue

            # Get sources from first January prompt for this query
            jan_prompt = jan_by_query[nov_prompt.query][0]
            jan_sources = get_sources_for_prompt(session, jan_prompt.id)

            if not jan_sources:
                continue

            # Remove ~25% of sources for November
            num_to_keep = max(1, int(len(jan_sources) * 0.75))
            sources_to_use = random.sample(jan_sources, num_to_keep)
            sources_to_use.sort(key=lambda x: x[1])  # Sort by original citation_order

            # Add sources with renumbered citation_order
            for idx, (source_id, _) in enumerate(sources_to_use, 1):
                # Check if already exists
                existing = session.exec(
                    select(PromptSource).where(
                        PromptSource.prompt_id == nov_prompt.id,
                        PromptSource.source_id == source_id
                    )
                ).first()

                if not existing:
                    new_ps = PromptSource(
                        prompt_id=nov_prompt.id,
                        source_id=source_id,
                        citation_order=idx
                    )
                    session.add(new_ps)
                    nov_sources_added += 1

            # Modify response_text
            if nov_prompt.response_text:
                nov_prompt.response_text = vary_response_text(nov_prompt.response_text, "nov")
                nov_responses_modified += 1

        # Process December prompts
        print("Processing December prompts...")
        for dec_prompt in dec_prompts:
            if dec_prompt.query not in jan_by_query:
                print(f"  Warning: No January data for query: {dec_prompt.query[:50]}...")
                continue

            # Get sources from first January prompt for this query
            jan_prompt = jan_by_query[dec_prompt.query][0]
            jan_sources = get_sources_for_prompt(session, jan_prompt.id)

            if not jan_sources:
                continue

            # Remove ~15% of sources for December
            num_to_keep = max(1, int(len(jan_sources) * 0.85))
            sources_to_use = random.sample(jan_sources, num_to_keep)
            sources_to_use.sort(key=lambda x: x[1])  # Sort by original citation_order

            # Add sources with renumbered citation_order
            for idx, (source_id, _) in enumerate(sources_to_use, 1):
                # Check if already exists
                existing = session.exec(
                    select(PromptSource).where(
                        PromptSource.prompt_id == dec_prompt.id,
                        PromptSource.source_id == source_id
                    )
                ).first()

                if not existing:
                    new_ps = PromptSource(
                        prompt_id=dec_prompt.id,
                        source_id=source_id,
                        citation_order=idx
                    )
                    session.add(new_ps)
                    dec_sources_added += 1

            # Modify response_text
            if dec_prompt.response_text:
                dec_prompt.response_text = vary_response_text(dec_prompt.response_text, "dec")
                dec_responses_modified += 1

        # Commit all changes
        session.commit()

        print(f"\nDone!")
        print(f"November: {nov_sources_added} sources added, {nov_responses_modified} responses modified")
        print(f"December: {dec_sources_added} sources added, {dec_responses_modified} responses modified")

        # Verify final counts
        nov_total = sum(1 for p in nov_prompts for _ in get_sources_for_prompt(session, p.id))
        dec_total = sum(1 for p in dec_prompts for _ in get_sources_for_prompt(session, p.id))
        jan_total = sum(1 for p in jan_prompts for _ in get_sources_for_prompt(session, p.id))

        print(f"\nFinal source counts:")
        print(f"  November: {nov_total}")
        print(f"  December: {dec_total}")
        print(f"  January:  {jan_total}")
        print(f"  Total:    {nov_total + dec_total + jan_total}")


if __name__ == "__main__":
    populate_historical_sources()

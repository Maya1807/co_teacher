"""
Main script to fetch data from all sources and seed to Pinecone.

Usage:
    python -m scrapers.seed_from_sources --all          # Fetch and seed everything
    python -m scrapers.seed_from_sources --fetch-only   # Only fetch, don't seed
    python -m scrapers.seed_from_sources --seed-only    # Only seed from existing JSON
    python -m scrapers.seed_from_sources --eric         # Only ERIC
    python -m scrapers.seed_from_sources --iris         # Only IRIS
    python -m scrapers.seed_from_sources --wikipedia    # Only Wikipedia
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from scrapers.eric_fetcher import ERICFetcher
from scrapers.iris_scraper import IRISScraper
from scrapers.wikipedia_fetcher import WikipediaFetcher
from scrapers.config import OUTPUT_DIR


async def fetch_eric_data(
    max_per_descriptor: int = 30,
    max_per_keyword: int = 20,
    min_year: int = 2018,
) -> list[dict]:
    """Fetch data from ERIC API."""
    print("\n" + "=" * 60)
    print("Fetching from ERIC API")
    print("=" * 60)

    fetcher = ERICFetcher()
    await fetcher.fetch_all_special_education(
        max_per_descriptor=max_per_descriptor,
        max_per_keyword=max_per_keyword,
        min_year=min_year,
    )
    fetcher.save_to_json()

    return fetcher.get_records_for_pinecone()


async def fetch_iris_data() -> list[dict]:
    """Fetch data from IRIS Center."""
    print("\n" + "=" * 60)
    print("Scraping IRIS Center")
    print("=" * 60)

    scraper = IRISScraper()
    await scraper.scrape_all()
    scraper.save_to_json()

    return scraper.get_records_for_pinecone()


async def fetch_wikipedia_data() -> list[dict]:
    """Fetch data from Wikipedia."""
    print("\n" + "=" * 60)
    print("Fetching from Wikipedia")
    print("=" * 60)

    fetcher = WikipediaFetcher()
    await fetcher.fetch_all()
    fetcher.save_to_json()

    return fetcher.get_records_for_pinecone()


def load_cached_data() -> tuple[list[dict], list[dict], list[dict]]:
    """Load previously fetched data from JSON files."""
    output_dir = Path(OUTPUT_DIR)
    eric_records = []
    iris_records = []
    wikipedia_records = []

    eric_file = output_dir / "eric_records.json"
    if eric_file.exists():
        print(f"Loading ERIC data from {eric_file}")
        with open(eric_file) as f:
            data = json.load(f)
            fetcher = ERICFetcher()
            fetcher.records = data.get("records", [])
            eric_records = fetcher.get_records_for_pinecone()
            print(f"  Loaded {len(eric_records)} ERIC records")

    iris_file = output_dir / "iris_content.json"
    if iris_file.exists():
        print(f"Loading IRIS data from {iris_file}")
        with open(iris_file) as f:
            data = json.load(f)
            scraper = IRISScraper()
            scraper.modules = data.get("modules", [])
            iris_records = scraper.get_records_for_pinecone()
            print(f"  Loaded {len(iris_records)} IRIS records")

    wikipedia_file = output_dir / "wikipedia_content.json"
    if wikipedia_file.exists():
        print(f"Loading Wikipedia data from {wikipedia_file}")
        with open(wikipedia_file) as f:
            data = json.load(f)
            fetcher = WikipediaFetcher()
            fetcher.articles = data.get("articles", [])
            wikipedia_records = fetcher.get_records_for_pinecone()
            print(f"  Loaded {len(wikipedia_records)} Wikipedia records")

    return eric_records, iris_records, wikipedia_records


async def seed_to_pinecone(records: list[dict], namespace: str = "teaching-methods"):
    """
    Seed records to Pinecone.

    Args:
        records: List of records with 'id', 'text', and 'metadata'
        namespace: Pinecone namespace to use
    """
    print("\n" + "=" * 60)
    print(f"Seeding {len(records)} records to Pinecone")
    print("=" * 60)

    # Import here to avoid circular imports
    from app.memory.pinecone_client import get_pinecone_client
    from app.core.llm_client import get_llm_client

    pinecone = get_pinecone_client()
    llm = get_llm_client()

    # Check if using mock
    if "Mock" in type(pinecone).__name__:
        print("WARNING: Using MockPineconeClient - data will not persist!")
        print("Set USE_MOCK_SERVICES=false in .env to use real Pinecone")

    success_count = 0
    error_count = 0

    for i, record in enumerate(records):
        try:
            # Generate embedding
            embedding = await llm.embed(record["text"])

            # Upsert to Pinecone
            await pinecone.upsert_teaching_method(
                method_id=record["id"],
                embedding=embedding,
                metadata=record["metadata"],
            )

            success_count += 1

            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{len(records)} records...")

        except Exception as e:
            error_count += 1
            print(f"  Error seeding {record['id']}: {e}")

    print(f"\nSeeding complete: {success_count} success, {error_count} errors")

    # Verify
    stats = await pinecone.get_index_stats()
    print(f"Pinecone stats: {stats}")


async def main():
    parser = argparse.ArgumentParser(
        description="Fetch educational content and seed to Pinecone"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Fetch from all sources and seed to Pinecone"
    )
    parser.add_argument(
        "--fetch-only", action="store_true",
        help="Only fetch data, don't seed to Pinecone"
    )
    parser.add_argument(
        "--seed-only", action="store_true",
        help="Only seed from existing JSON files"
    )
    parser.add_argument(
        "--eric", action="store_true",
        help="Only process ERIC data"
    )
    parser.add_argument(
        "--iris", action="store_true",
        help="Only process IRIS data"
    )
    parser.add_argument(
        "--wikipedia", action="store_true",
        help="Only process Wikipedia data"
    )
    parser.add_argument(
        "--min-year", type=int, default=2018,
        help="Minimum publication year for ERIC (default: 2018)"
    )
    parser.add_argument(
        "--max-results", type=int, default=30,
        help="Max results per ERIC descriptor (default: 30)"
    )

    args = parser.parse_args()

    # Default to --all if no specific source given
    if not any([args.all, args.seed_only, args.eric, args.iris, args.wikipedia]):
        args.all = True

    # --fetch-only implies we want to fetch all sources unless specific ones given
    if args.fetch_only and not any([args.eric, args.iris, args.wikipedia]):
        args.all = True

    print("=" * 60)
    print("Educational Content Fetcher & Seeder")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    all_records = []

    if args.seed_only:
        # Load from existing files
        eric_records, iris_records, wikipedia_records = load_cached_data()
        if args.eric:
            all_records.extend(eric_records)
        elif args.iris:
            all_records.extend(iris_records)
        elif args.wikipedia:
            all_records.extend(wikipedia_records)
        else:
            # Load all if no specific source
            all_records.extend(eric_records)
            all_records.extend(iris_records)
            all_records.extend(wikipedia_records)
    else:
        # Fetch fresh data
        if args.all or args.eric:
            eric_records = await fetch_eric_data(
                max_per_descriptor=args.max_results,
                min_year=args.min_year,
            )
            all_records.extend(eric_records)

        if args.all or args.iris:
            iris_records = await fetch_iris_data()
            all_records.extend(iris_records)

        if args.all or args.wikipedia:
            wikipedia_records = await fetch_wikipedia_data()
            all_records.extend(wikipedia_records)

    print(f"\nTotal records to seed: {len(all_records)}")

    # Seed to Pinecone unless fetch-only
    if not args.fetch_only and all_records:
        await seed_to_pinecone(all_records)

    print("\n" + "=" * 60)
    print(f"Completed: {datetime.now().isoformat()}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

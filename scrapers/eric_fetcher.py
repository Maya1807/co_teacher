"""
ERIC API Fetcher for education research abstracts.

ERIC (Education Resources Information Center) provides access to education research
and information. This fetcher retrieves relevant special education research.

API Documentation: https://eric.ed.gov/?api
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import httpx

from scrapers.config import (
    ERIC_API_BASE,
    ERIC_DESCRIPTORS,
    ERIC_KEYWORDS,
    DISABILITY_MAPPINGS,
    REQUEST_DELAY,
    MAX_RETRIES,
    OUTPUT_DIR,
)


class ERICFetcher:
    """Fetches education research from ERIC API."""

    def __init__(self, output_dir: Optional[str] = None):
        self.base_url = ERIC_API_BASE
        self.output_dir = Path(output_dir or OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.records = []

    async def search(
        self,
        query: str,
        rows: int = 50,
        start: int = 0,
        pub_date_min: Optional[int] = None,
    ) -> dict:
        """
        Search ERIC database.

        Args:
            query: Search query (can use ERIC syntax)
            rows: Number of results to return (max 200)
            start: Starting offset for pagination
            pub_date_min: Minimum publication year

        Returns:
            API response as dict
        """
        params = {
            "search": query,
            "rows": min(rows, 200),
            "start": start,
            "format": "json",
        }

        if pub_date_min:
            params["publicationdatemin"] = f"{pub_date_min}-01-01"

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(MAX_RETRIES):
                try:
                    response = await client.get(self.base_url, params=params)
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPError as e:
                    if attempt < MAX_RETRIES - 1:
                        print(f"  Retry {attempt + 1}/{MAX_RETRIES} after error: {e}")
                        await asyncio.sleep(REQUEST_DELAY * 2)
                    else:
                        raise

    async def fetch_by_descriptor(
        self,
        descriptor: str,
        max_results: int = 100,
        min_year: int = 2015,
    ) -> list[dict]:
        """
        Fetch records by ERIC descriptor/keyword.

        Args:
            descriptor: Search term (e.g., "autism teaching strategies")
            max_results: Maximum number of results
            min_year: Minimum publication year

        Returns:
            List of ERIC records
        """
        print(f"  Fetching: {descriptor}...")
        # Use simple keyword search (descriptor syntax not supported in this API version)
        query = descriptor

        records = []
        start = 0
        batch_size = 50

        while len(records) < max_results:
            result = await self.search(
                query=query,
                rows=min(batch_size, max_results - len(records)),
                start=start,
                pub_date_min=min_year,
            )

            docs = result.get("response", {}).get("docs", [])
            if not docs:
                break

            records.extend(docs)
            start += len(docs)

            if len(docs) < batch_size:
                break

            await asyncio.sleep(REQUEST_DELAY)

        print(f"    Found {len(records)} records")
        return records

    async def fetch_by_keyword(
        self,
        keyword: str,
        max_results: int = 50,
        min_year: int = 2015,
    ) -> list[dict]:
        """
        Fetch records by keyword search.

        Args:
            keyword: Search keyword or phrase
            max_results: Maximum number of results
            min_year: Minimum publication year

        Returns:
            List of ERIC records
        """
        print(f"  Searching: {keyword}...")
        query = keyword

        result = await self.search(
            query=query,
            rows=max_results,
            pub_date_min=min_year,
        )

        docs = result.get("response", {}).get("docs", [])
        print(f"    Found {len(docs)} records")
        return docs

    def parse_record(self, record: dict) -> dict:
        """
        Parse ERIC record into our format.

        Args:
            record: Raw ERIC API record

        Returns:
            Parsed record with standardized fields
        """
        # Extract relevant fields
        parsed = {
            "id": record.get("id", ""),
            "title": record.get("title", ""),
            "abstract": record.get("description", ""),
            "authors": record.get("author", []),
            "publication_date": record.get("publicationdateyear", ""),
            "source": record.get("source", ""),
            "descriptors": record.get("subject", []),
            "education_level": record.get("educationlevel", []),
            "url": f"https://eric.ed.gov/?id={record.get('id', '')}",
            "peer_reviewed": record.get("peerreviewed", False),
            "source_type": "eric_research",
        }

        # Determine disability categories based on descriptors
        parsed["disability_categories"] = self._categorize_by_disability(
            parsed["descriptors"] + [parsed["title"]] + [parsed["abstract"]]
        )

        return parsed

    def _categorize_by_disability(self, text_fields: list) -> list[str]:
        """Categorize record by disability type based on content."""
        text = " ".join(str(f).lower() for f in text_fields)
        categories = []

        for category, keywords in DISABILITY_MAPPINGS.items():
            if any(kw in text for kw in keywords):
                categories.append(category)

        return categories if categories else ["general"]

    async def fetch_all_special_education(
        self,
        max_per_descriptor: int = 50,
        max_per_keyword: int = 30,
        min_year: int = 2015,
    ) -> list[dict]:
        """
        Fetch comprehensive special education research.

        Args:
            max_per_descriptor: Max results per ERIC descriptor
            max_per_keyword: Max results per keyword search
            min_year: Minimum publication year

        Returns:
            List of all parsed records
        """
        all_records = {}  # Use dict to dedupe by ID

        print("\nFetching by ERIC descriptors...")
        for descriptor in ERIC_DESCRIPTORS:
            try:
                records = await self.fetch_by_descriptor(
                    descriptor, max_per_descriptor, min_year
                )
                for record in records:
                    parsed = self.parse_record(record)
                    if parsed["abstract"]:  # Only keep records with abstracts
                        all_records[parsed["id"]] = parsed
                await asyncio.sleep(REQUEST_DELAY)
            except Exception as e:
                print(f"    Error fetching {descriptor}: {e}")

        print("\nFetching by keywords...")
        for keyword in ERIC_KEYWORDS:
            try:
                records = await self.fetch_by_keyword(
                    keyword, max_per_keyword, min_year
                )
                for record in records:
                    parsed = self.parse_record(record)
                    if parsed["abstract"]:
                        all_records[parsed["id"]] = parsed
                await asyncio.sleep(REQUEST_DELAY)
            except Exception as e:
                print(f"    Error fetching {keyword}: {e}")

        self.records = list(all_records.values())
        print(f"\nTotal unique records with abstracts: {len(self.records)}")
        return self.records

    def save_to_json(self, filename: str = "eric_records.json") -> Path:
        """Save fetched records to JSON file."""
        output_path = self.output_dir / filename

        output = {
            "metadata": {
                "source": "ERIC API",
                "fetched_at": datetime.now().isoformat(),
                "total_records": len(self.records),
            },
            "records": self.records,
        }

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        print(f"Saved {len(self.records)} records to {output_path}")
        return output_path

    def get_records_for_pinecone(self, use_chunking: bool = True) -> list[dict]:
        """
        Format records for Pinecone ingestion with optional chunking.

        Args:
            use_chunking: Whether to chunk documents (default True)

        Returns:
            List of records formatted for embedding and storage
        """
        from scrapers.chunker import chunk_document

        pinecone_records = []

        for record in self.records:
            # Create text for embedding
            text_for_embedding = f"""
Title: {record['title']}

Abstract: {record['abstract']}

Topics: {', '.join(record['descriptors'][:10])}
            """.strip()

            base_metadata = {
                "source_type": "eric_research",
                "title": record["title"],
                "authors": record["authors"][:5],
                "year": record["publication_date"],
                "url": record["url"],
                "disability_categories": record["disability_categories"],
                "descriptors": record["descriptors"][:10],
                "peer_reviewed": record["peer_reviewed"],
            }

            doc_id = f"eric_{record['id']}"

            if use_chunking:
                # Chunk the document
                chunks = chunk_document(
                    doc_id=doc_id,
                    text=text_for_embedding,
                    metadata=base_metadata,
                    chunk_size=1000,
                    overlap_percent=0.18
                )
                pinecone_records.extend(chunks)
            else:
                # Single record (for small documents)
                base_metadata["abstract"] = record["abstract"][:1000]
                pinecone_records.append({
                    "id": doc_id,
                    "text": text_for_embedding,
                    "metadata": base_metadata,
                })

        return pinecone_records


async def main():
    """Test the ERIC fetcher."""
    fetcher = ERICFetcher()

    print("=" * 60)
    print("ERIC API Fetcher - Special Education Research")
    print("=" * 60)

    # Fetch all special education content
    records = await fetcher.fetch_all_special_education(
        max_per_descriptor=30,
        max_per_keyword=20,
        min_year=2018,
    )

    # Save to JSON
    fetcher.save_to_json()

    # Show sample
    if records:
        print("\nSample record:")
        sample = records[0]
        print(f"  Title: {sample['title'][:80]}...")
        print(f"  Categories: {sample['disability_categories']}")
        print(f"  Descriptors: {sample['descriptors'][:5]}")


if __name__ == "__main__":
    asyncio.run(main())

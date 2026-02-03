"""
Wikipedia Fetcher for special education foundational knowledge.

Uses the MediaWiki API to fetch article content about disabilities,
educational strategies, and special education concepts.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from scrapers.config import (
    DISABILITY_MAPPINGS,
    REQUEST_DELAY,
    OUTPUT_DIR,
)


# Wikipedia articles to fetch for foundational knowledge
WIKIPEDIA_ARTICLES = [
    # Core special education concepts
    "Special education",
    "Individualized Education Program",
    "Response to intervention",
    "Individuals with Disabilities Education Act",
    "Section 504 of the Rehabilitation Act",
    "Universal Design for Learning",
    "Inclusion (education)",

    # Disabilities and conditions
    "Autism spectrum disorder",
    "Attention deficit hyperactivity disorder",
    "Dyslexia",
    "Dyscalculia",
    "Dysgraphia",
    "Learning disability",
    "Intellectual disability",
    "Emotional and behavioral disorders",
    "Sensory processing disorder",
    "Executive dysfunction",

    # Interventions and strategies
    "Applied behavior analysis",
    "Positive behavior support",
    "Behavior modification",
    "Assistive technology",
    "Augmentative and alternative communication",
    "Social skills training",
    "Direct instruction",
    "Differentiated instruction",

    # Assessment and planning
    "Functional behavior assessment",
    "Curriculum-based measurement",
    "Progress monitoring",
]


class WikipediaFetcher:
    """Fetches educational content from Wikipedia via MediaWiki API."""

    def __init__(self, output_dir: Optional[str] = None):
        self.api_url = "https://en.wikipedia.org/w/api.php"
        self.output_dir = Path(output_dir or OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.articles = []

    async def fetch_article(self, title: str) -> Optional[dict]:
        """
        Fetch a single Wikipedia article.

        Args:
            title: Article title (e.g., "Autism spectrum disorder")

        Returns:
            Article data with title, content, and metadata
        """
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "extracts|info|categories",
            "explaintext": True,  # Plain text instead of HTML
            "exsectionformat": "plain",
            "inprop": "url",
            "cllimit": 20,  # Limit categories
            "redirects": 1,  # Follow redirects
        }

        headers = {
            "User-Agent": "Co-Teacher Educational Bot/1.0 (Educational Research Project)"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    self.api_url,
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

                # Extract page data
                pages = data.get("query", {}).get("pages", {})
                if not pages:
                    print(f"    No data returned for: {title}")
                    return None

                # Get first (and should be only) page
                page_id, page_data = next(iter(pages.items()))

                if page_id == "-1":
                    print(f"    Article not found: {title}")
                    return None

                extract = page_data.get("extract", "")
                if not extract:
                    print(f"    No content for: {title}")
                    return None

                # Clean and truncate content
                content = self._clean_content(extract)

                # Get categories for disability mapping
                categories = [
                    cat.get("title", "").replace("Category:", "")
                    for cat in page_data.get("categories", [])
                ]

                return {
                    "id": f"wiki_{self._slugify(title)}",
                    "title": page_data.get("title", title),
                    "url": page_data.get("fullurl", f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"),
                    "content": content,
                    "summary": content[:500] + "..." if len(content) > 500 else content,
                    "categories": categories,
                    "source_type": "wikipedia",
                    "disability_categories": self._infer_disabilities(title, content),
                    "fetched_at": datetime.now().isoformat(),
                }

            except httpx.HTTPError as e:
                print(f"    Error fetching {title}: {e}")
                return None

    def _clean_content(self, text: str, max_length: int = 8000) -> str:
        """Clean Wikipedia article content."""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)

        # Remove common Wikipedia artifacts
        text = re.sub(r'==+\s*See also\s*==+.*', '', text, flags=re.DOTALL)
        text = re.sub(r'==+\s*References\s*==+.*', '', text, flags=re.DOTALL)
        text = re.sub(r'==+\s*External links\s*==+.*', '', text, flags=re.DOTALL)
        text = re.sub(r'==+\s*Further reading\s*==+.*', '', text, flags=re.DOTALL)
        text = re.sub(r'==+\s*Notes\s*==+.*', '', text, flags=re.DOTALL)

        # Clean up section headers (keep but simplify)
        text = re.sub(r'==+\s*', '\n## ', text)
        text = re.sub(r'\s*==+', '\n', text)

        # Truncate to max length at sentence boundary
        if len(text) > max_length:
            text = text[:max_length]
            last_period = text.rfind('.')
            if last_period > max_length * 0.8:
                text = text[:last_period + 1]

        return text.strip()

    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
        slug = text.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '_', slug)
        return slug[:50]

    def _infer_disabilities(self, title: str, content: str) -> list[str]:
        """Infer disability categories from content."""
        text = f"{title} {content[:2000]}".lower()
        categories = []

        for disability, keywords in DISABILITY_MAPPINGS.items():
            if any(kw in text for kw in keywords):
                categories.append(disability)

        # Add based on title keywords
        title_lower = title.lower()
        if "autism" in title_lower or "asd" in title_lower:
            if "autism" not in categories:
                categories.append("autism")
        if "adhd" in title_lower or "attention deficit" in title_lower:
            if "adhd" not in categories:
                categories.append("adhd")
        if "dyslexia" in title_lower or "reading" in title_lower:
            if "learning_disabilities" not in categories:
                categories.append("learning_disabilities")
        if "behavior" in title_lower or "emotional" in title_lower:
            if "emotional_behavioral" not in categories:
                categories.append("emotional_behavioral")

        return categories if categories else ["general"]

    async def fetch_all(
        self,
        articles: Optional[list[str]] = None,
        max_articles: Optional[int] = None
    ) -> list[dict]:
        """
        Fetch all configured Wikipedia articles.

        Args:
            articles: Optional list of article titles (defaults to WIKIPEDIA_ARTICLES)
            max_articles: Optional limit on number of articles

        Returns:
            List of fetched articles
        """
        article_list = articles or WIKIPEDIA_ARTICLES
        if max_articles:
            article_list = article_list[:max_articles]

        print(f"\nFetching {len(article_list)} Wikipedia articles...")

        for title in article_list:
            print(f"  Fetching: {title}...")
            article = await self.fetch_article(title)
            if article:
                self.articles.append(article)
                print(f"    ✓ {len(article['content'])} chars")
            await asyncio.sleep(REQUEST_DELAY)

        print(f"\nTotal articles fetched: {len(self.articles)}")
        return self.articles

    def save_to_json(self, filename: str = "wikipedia_content.json") -> Path:
        """Save fetched articles to JSON file."""
        output_path = self.output_dir / filename

        output = {
            "metadata": {
                "source": "Wikipedia (MediaWiki API)",
                "fetched_at": datetime.now().isoformat(),
                "total_articles": len(self.articles),
            },
            "articles": self.articles,
        }

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        print(f"Saved {len(self.articles)} articles to {output_path}")
        return output_path

    def get_records_for_pinecone(self, use_chunking: bool = True) -> list[dict]:
        """
        Format articles for Pinecone ingestion with chunking.

        Wikipedia articles are large and benefit significantly from chunking.

        Args:
            use_chunking: Whether to chunk documents (default True, highly recommended)

        Returns:
            List of records formatted for embedding and storage
        """
        from scrapers.chunker import chunk_document

        pinecone_records = []

        for article in self.articles:
            # Create text for embedding
            text_for_embedding = f"""
Topic: {article['title']}

{article['content']}
            """.strip()

            base_metadata = {
                "source_type": "wikipedia",
                "title": article["title"],
                "url": article["url"],
                "disability_categories": article["disability_categories"],
                "wikipedia_categories": article["categories"][:10],
            }

            doc_id = article["id"]

            if use_chunking:
                # Chunk the document - Wikipedia articles especially benefit
                chunks = chunk_document(
                    doc_id=doc_id,
                    text=text_for_embedding,
                    metadata=base_metadata,
                    chunk_size=1000,
                    overlap_percent=0.18
                )
                pinecone_records.extend(chunks)
            else:
                # Single record (not recommended for Wikipedia)
                base_metadata["summary"] = article["summary"]
                pinecone_records.append({
                    "id": doc_id,
                    "text": text_for_embedding[:10000],
                    "metadata": base_metadata,
                })

        return pinecone_records


async def main():
    """Test the Wikipedia fetcher."""
    print("=" * 60)
    print("Wikipedia Fetcher - Educational Content")
    print("=" * 60)

    fetcher = WikipediaFetcher()

    # Fetch all articles
    await fetcher.fetch_all()

    # Save to JSON
    fetcher.save_to_json()

    # Show sample
    if fetcher.articles:
        print("\nSample article:")
        sample = fetcher.articles[0]
        print(f"  Title: {sample['title']}")
        print(f"  URL: {sample['url']}")
        print(f"  Content length: {len(sample['content'])} chars")
        print(f"  Categories: {sample['disability_categories']}")
        print(f"\n  Preview: {sample['summary'][:200]}...")

    # Show stats
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total articles: {len(fetcher.articles)}")
    total_chars = sum(len(a['content']) for a in fetcher.articles)
    print(f"Total content: {total_chars:,} characters")

    # Get Pinecone records
    records = fetcher.get_records_for_pinecone()
    print(f"Pinecone records: {len(records)}")


if __name__ == "__main__":
    asyncio.run(main())

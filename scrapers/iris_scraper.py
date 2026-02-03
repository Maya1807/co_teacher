"""
IRIS Center Scraper for teaching modules and strategies.

The IRIS Center (iris.peabody.vanderbilt.edu) provides free, evidence-based
resources for teaching students with disabilities. This scraper extracts
module content, strategies, and case studies.

Note: IRIS Center is federally funded (OSEP) and provides free educational resources.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from scrapers.config import (
    IRIS_BASE_URL,
    IRIS_MODULES,
    IRIS_RESOURCE_PAGES,
    DISABILITY_MAPPINGS,
    REQUEST_DELAY,
    MAX_RETRIES,
    OUTPUT_DIR,
)


class IRISScraper:
    """Scrapes teaching content from IRIS Center."""

    def __init__(self, output_dir: Optional[str] = None):
        self.base_url = IRIS_BASE_URL
        self.output_dir = Path(output_dir or OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.modules = []
        self.strategies = []

    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with retry logic."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Educational Research Bot - Co-Teacher Project)"
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for attempt in range(MAX_RETRIES):
                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    return response.text
                except httpx.HTTPError as e:
                    if attempt < MAX_RETRIES - 1:
                        print(f"    Retry {attempt + 1}/{MAX_RETRIES}: {e}")
                        await asyncio.sleep(REQUEST_DELAY * 2)
                    else:
                        print(f"    Failed to fetch {url}: {e}")
                        return None

    def clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,;:!?\-\'\"()]', ' ', text)
        return text.strip()

    async def scrape_module(self, module_path: str, category: str) -> Optional[dict]:
        """
        Scrape a single IRIS module.

        Args:
            module_path: Path to module (e.g., "/module/asd1/")
            category: Category this module belongs to

        Returns:
            Parsed module data
        """
        url = urljoin(self.base_url, module_path)
        print(f"  Scraping: {url}")

        html = await self.fetch_page(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")

        # Extract module title from <title> tag (most reliable)
        title_elem = soup.find("title")
        title = self.clean_text(title_elem.get_text()) if title_elem else "Unknown Module"

        # Remove "IRIS Center" suffix from title if present
        title = re.sub(r'\s*\|\s*IRIS.*$', '', title)
        title = re.sub(r'\s*-\s*IRIS.*$', '', title)
        title = re.sub(r'\s*–\s*IRIS.*$', '', title)

        # Extract all text content from the page
        # IRIS uses JavaScript for content, so we get what's in static HTML
        all_text = []
        for elem in soup.find_all(["p", "li", "h2", "h3", "h4"]):
            text = self.clean_text(elem.get_text())
            if len(text) > 20:
                all_text.append(text)

        # Use meta description if available
        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = ""
        if meta_desc and meta_desc.get("content"):
            description = self.clean_text(meta_desc["content"])

        # If no meta description, use collected text
        if not description and all_text:
            description = " ".join(all_text[:5])

        # Extract any list items as potential strategies
        strategies = []
        for li in soup.find_all("li"):
            text = self.clean_text(li.get_text())
            if 20 < len(text) < 300:  # Filter reasonable length items
                strategies.append(text)

        # Build module data - use title-based descriptions for known modules
        module_descriptions = self._get_module_descriptions()
        module_key = module_path.strip("/").replace("/", "_")

        if module_key in module_descriptions:
            desc_data = module_descriptions[module_key]
            description = desc_data.get("description", description)
            if not strategies:
                strategies = desc_data.get("strategies", [])

        module_data = {
            "id": module_key,
            "title": title,
            "url": url,
            "category": category,
            "description": description[:2000] if description else f"IRIS module on {title}",
            "objectives": [],
            "strategies": strategies[:20],
            "resources": [],
            "source_type": "iris_module",
            "disability_categories": self._infer_disabilities(title, description, category),
        }

        return module_data

    def _get_module_descriptions(self) -> dict:
        """Return curated descriptions for known IRIS modules."""
        return {
            "module_fba": {
                "description": "Functional Behavioral Assessment (FBA) is a process for identifying the function or purpose of a student's behavior. This module covers how to conduct an FBA, identify antecedents and consequences, and develop behavior intervention plans.",
                "strategies": [
                    "Identify the target behavior in observable, measurable terms",
                    "Collect data on antecedents (what happens before the behavior)",
                    "Document consequences (what happens after the behavior)",
                    "Determine the function of the behavior (attention, escape, tangible, sensory)",
                    "Develop a hypothesis about why the behavior occurs",
                    "Create a Behavior Intervention Plan (BIP) based on the function"
                ]
            },
            "module_asd1": {
                "description": "Understanding Autism Spectrum Disorder: characteristics, early signs, and evidence-based practices for supporting students with autism in educational settings.",
                "strategies": [
                    "Use visual supports and schedules",
                    "Provide clear, concrete instructions",
                    "Create structured, predictable environments",
                    "Use social stories for new situations",
                    "Implement sensory accommodations",
                    "Provide advance warning for transitions"
                ]
            },
            "module_asd2": {
                "description": "Evidence-based practices for teaching students with Autism Spectrum Disorder, including communication strategies, social skills instruction, and behavioral supports.",
                "strategies": [
                    "Implement structured teaching methods",
                    "Use augmentative and alternative communication (AAC)",
                    "Teach social skills explicitly",
                    "Apply applied behavior analysis (ABA) techniques",
                    "Create peer support systems",
                    "Use video modeling for skill instruction"
                ]
            },
            "module_bi1": {
                "description": "Behavior Intervention Part 1: Understanding the principles of behavior and how to use positive behavioral interventions and supports in the classroom.",
                "strategies": [
                    "Establish clear behavioral expectations",
                    "Teach expected behaviors explicitly",
                    "Provide positive reinforcement for appropriate behavior",
                    "Use consistent consequences",
                    "Monitor student behavior systematically"
                ]
            },
            "module_bi2": {
                "description": "Behavior Intervention Part 2: Advanced strategies for addressing challenging behaviors, including function-based interventions and crisis prevention.",
                "strategies": [
                    "Conduct functional behavior assessments",
                    "Develop individualized behavior intervention plans",
                    "Implement replacement behavior training",
                    "Use de-escalation techniques",
                    "Monitor and adjust interventions based on data"
                ]
            },
            "module_pbis": {
                "description": "Positive Behavioral Interventions and Supports (PBIS): A framework for creating positive school environments through prevention, teaching, and reinforcement of expected behaviors.",
                "strategies": [
                    "Define and teach school-wide expectations",
                    "Create a positive school climate",
                    "Use a tiered system of support (Tier 1, 2, 3)",
                    "Collect and use data for decision-making",
                    "Acknowledge and reward positive behavior",
                    "Provide targeted interventions for at-risk students"
                ]
            },
            "module_sr": {
                "description": "Self-Regulation: Teaching students to manage their emotions, behaviors, and learning through metacognitive strategies and self-monitoring techniques.",
                "strategies": [
                    "Teach emotional awareness and vocabulary",
                    "Use self-monitoring checklists",
                    "Implement calming strategies and zones",
                    "Practice goal-setting and self-evaluation",
                    "Create visual supports for self-regulation",
                    "Use cognitive behavioral strategies"
                ]
            },
            "module_di": {
                "description": "Differentiated Instruction: Tailoring instruction to meet the diverse needs of learners through varied content, process, product, and learning environment.",
                "strategies": [
                    "Pre-assess student readiness and interests",
                    "Provide tiered assignments",
                    "Use flexible grouping strategies",
                    "Offer choice in how students demonstrate learning",
                    "Adjust content complexity based on student needs",
                    "Use learning stations and centers"
                ]
            },
            "module_udl": {
                "description": "Universal Design for Learning (UDL): A framework for designing flexible learning experiences that accommodate all learners through multiple means of engagement, representation, and action/expression.",
                "strategies": [
                    "Provide multiple means of engagement (the 'why' of learning)",
                    "Offer multiple means of representation (the 'what' of learning)",
                    "Allow multiple means of action and expression (the 'how' of learning)",
                    "Remove barriers proactively in lesson design",
                    "Use technology to increase accessibility",
                    "Provide options for self-regulation and executive function"
                ]
            },
            "module_pm": {
                "description": "Progress Monitoring: Systematically assessing student progress toward academic and behavioral goals to inform instruction and intervention decisions.",
                "strategies": [
                    "Select appropriate assessment measures",
                    "Establish baseline performance levels",
                    "Set ambitious but achievable goals",
                    "Collect data frequently and consistently",
                    "Graph and analyze data regularly",
                    "Adjust instruction based on student response"
                ]
            },
            "module_coteach": {
                "description": "Co-Teaching: Collaborative teaching models where general and special education teachers work together to provide instruction to all students in inclusive settings.",
                "strategies": [
                    "Establish parity and shared responsibility",
                    "Use various co-teaching models (team, station, parallel, alternative, one teach/one assist)",
                    "Plan collaboratively for instruction",
                    "Share classroom management responsibilities",
                    "Differentiate instruction for diverse learners"
                ]
            },
        }

    async def scrape_resource_page(self, page_path: str) -> list[dict]:
        """
        Scrape an IRIS resource listing page.

        Args:
            page_path: Path to resource page

        Returns:
            List of resource items
        """
        url = urljoin(self.base_url, page_path)
        print(f"  Scraping resource page: {url}")

        html = await self.fetch_page(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        resources = []

        # Find all resource cards/items
        for item in soup.find_all(["article", "div"], class_=re.compile(r"resource|card|item")):
            title_elem = item.find(["h2", "h3", "h4", "a"])
            if not title_elem:
                continue

            title = self.clean_text(title_elem.get_text())

            # Get link
            link = item.find("a", href=True)
            item_url = urljoin(self.base_url, link["href"]) if link else ""

            # Get description
            desc_elem = item.find("p") or item.find("div", class_="description")
            description = self.clean_text(desc_elem.get_text()) if desc_elem else ""

            if title and len(title) > 5:
                resources.append({
                    "id": f"iris_resource_{len(resources)}",
                    "title": title,
                    "url": item_url,
                    "description": description[:500],
                    "source_type": "iris_resource",
                    "disability_categories": self._infer_disabilities(title, description, ""),
                })

        return resources

    def _infer_disabilities(self, title: str, description: str, category: str) -> list[str]:
        """Infer disability categories from content."""
        text = f"{title} {description} {category}".lower()
        categories = []

        for disability, keywords in DISABILITY_MAPPINGS.items():
            if any(kw in text for kw in keywords):
                categories.append(disability)

        # Map IRIS category to disability if no match found
        if not categories:
            category_map = {
                "autism": ["autism"],
                "behavior": ["emotional_behavioral"],
                "learning_disabilities": ["learning_disabilities"],
                "instruction": ["general"],
                "assessment": ["general"],
                "collaboration": ["general"],
                "classroom_management": ["emotional_behavioral"],
                "transition": ["general"],
            }
            categories = category_map.get(category, ["general"])

        return categories

    async def scrape_all_modules(self) -> list[dict]:
        """Scrape all configured IRIS modules."""
        all_modules = []

        print("\nScraping IRIS modules...")
        for category, module_paths in IRIS_MODULES.items():
            print(f"\nCategory: {category}")
            for path in module_paths:
                try:
                    module = await self.scrape_module(path, category)
                    if module:
                        all_modules.append(module)
                        print(f"    ✓ {module['title'][:50]}...")
                    await asyncio.sleep(REQUEST_DELAY)
                except Exception as e:
                    print(f"    ✗ Error scraping {path}: {e}")

        self.modules = all_modules
        print(f"\nTotal modules scraped: {len(self.modules)}")
        return self.modules

    async def scrape_all_resources(self) -> list[dict]:
        """Scrape all resource pages."""
        all_resources = []

        print("\nScraping IRIS resource pages...")
        for page_path in IRIS_RESOURCE_PAGES:
            try:
                resources = await self.scrape_resource_page(page_path)
                all_resources.extend(resources)
                print(f"  Found {len(resources)} resources")
                await asyncio.sleep(REQUEST_DELAY)
            except Exception as e:
                print(f"  Error scraping {page_path}: {e}")

        print(f"Total resources scraped: {len(all_resources)}")
        return all_resources

    async def scrape_all(self) -> dict:
        """Scrape all IRIS content."""
        modules = await self.scrape_all_modules()
        resources = await self.scrape_all_resources()

        return {
            "modules": modules,
            "resources": resources,
        }

    def save_to_json(self, filename: str = "iris_content.json") -> Path:
        """Save scraped content to JSON file."""
        output_path = self.output_dir / filename

        output = {
            "metadata": {
                "source": "IRIS Center (Vanderbilt University)",
                "url": self.base_url,
                "scraped_at": datetime.now().isoformat(),
                "total_modules": len(self.modules),
            },
            "modules": self.modules,
        }

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        print(f"Saved {len(self.modules)} modules to {output_path}")
        return output_path

    def get_records_for_pinecone(self, use_chunking: bool = True) -> list[dict]:
        """
        Format scraped content for Pinecone ingestion with optional chunking.

        Args:
            use_chunking: Whether to chunk documents (default True)

        Returns:
            List of records formatted for embedding and storage
        """
        from scrapers.chunker import chunk_document

        pinecone_records = []

        for module in self.modules:
            # Create comprehensive text for embedding
            strategies_text = "\n".join(f"- {s}" for s in module.get("strategies", []))
            objectives_text = "\n".join(f"- {o}" for o in module.get("objectives", []))

            text_for_embedding = f"""
Module: {module['title']}
Category: {module['category']}

Description: {module['description']}

Learning Objectives:
{objectives_text}

Strategies and Techniques:
{strategies_text}
            """.strip()

            base_metadata = {
                "source_type": "iris_module",
                "title": module["title"],
                "category": module["category"],
                "url": module["url"],
                "disability_categories": module["disability_categories"],
                "strategies": module.get("strategies", [])[:10],
                "objectives": module.get("objectives", [])[:5],
            }

            doc_id = f"iris_{module['id']}"

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
                # Single record
                base_metadata["description"] = module["description"][:500]
                pinecone_records.append({
                    "id": doc_id,
                    "text": text_for_embedding,
                    "metadata": base_metadata,
                })

        return pinecone_records


async def main():
    """Test the IRIS scraper."""
    scraper = IRISScraper()

    print("=" * 60)
    print("IRIS Center Scraper - Teaching Modules")
    print("=" * 60)

    # Scrape all content
    await scraper.scrape_all()

    # Save to JSON
    scraper.save_to_json()

    # Show sample
    if scraper.modules:
        print("\nSample module:")
        sample = scraper.modules[0]
        print(f"  Title: {sample['title']}")
        print(f"  Category: {sample['category']}")
        print(f"  Strategies: {len(sample.get('strategies', []))}")


if __name__ == "__main__":
    asyncio.run(main())

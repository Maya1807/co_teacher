# Educational Content Scrapers

This package fetches real educational content from authoritative sources to populate the RAG knowledge base.

## Sources

### 1. ERIC API (Education Resources Information Center)
- **URL**: https://eric.ed.gov
- **Content**: Peer-reviewed education research abstracts
- **Access**: Free public API
- **Best for**: Evidence-based research backing, academic citations

### 2. IRIS Center (Vanderbilt University)
- **URL**: https://iris.peabody.vanderbilt.edu
- **Content**: Teaching modules, strategies, case studies
- **Access**: Web scraping (federally funded, free educational resource)
- **Best for**: Practical teaching strategies, structured learning modules

## Usage

### Install dependencies
```bash
pip install -r requirements.txt
```

### Fetch and seed all data
```bash
python -m scrapers.seed_from_sources --all
```

### Options
```bash
# Fetch only (don't seed to Pinecone)
python -m scrapers.seed_from_sources --fetch-only

# Seed from existing JSON files
python -m scrapers.seed_from_sources --seed-only

# Only ERIC data
python -m scrapers.seed_from_sources --eric

# Only IRIS data
python -m scrapers.seed_from_sources --iris

# Custom ERIC settings
python -m scrapers.seed_from_sources --eric --min-year 2020 --max-results 50
```

### Run individual scrapers
```bash
# Test ERIC fetcher
python -m scrapers.eric_fetcher

# Test IRIS scraper
python -m scrapers.iris_scraper
```

## Output

Scraped data is saved to `data/scraped/`:
- `eric_records.json` - ERIC research abstracts
- `iris_content.json` - IRIS teaching modules

## Data Format

### ERIC Records
```json
{
  "id": "eric_EJ1234567",
  "text": "Title + Abstract for embedding",
  "metadata": {
    "source_type": "eric_research",
    "title": "...",
    "abstract": "...",
    "authors": ["..."],
    "year": 2023,
    "url": "https://eric.ed.gov/?id=EJ1234567",
    "disability_categories": ["autism", "adhd"],
    "peer_reviewed": true
  }
}
```

### IRIS Modules
```json
{
  "id": "iris_module_asd1",
  "text": "Module content for embedding",
  "metadata": {
    "source_type": "iris_module",
    "title": "Autism Spectrum Disorder",
    "category": "autism",
    "description": "...",
    "url": "https://iris.peabody.vanderbilt.edu/module/asd1/",
    "disability_categories": ["autism"],
    "strategies": ["Visual schedules", "Social stories", ...],
    "objectives": ["...", ...]
  }
}
```

## Disability Categories

Records are automatically categorized into:
- `autism` - Autism Spectrum Disorders
- `adhd` - Attention Deficit Hyperactivity Disorder
- `learning_disabilities` - Dyslexia, Dyscalculia, etc.
- `emotional_behavioral` - Emotional/Behavioral Disorders
- `sensory_processing` - Sensory Processing Disorders
- `intellectual` - Intellectual Disabilities
- `general` - General special education

## Rate Limiting

Both scrapers include:
- 1 second delay between requests
- 3 retry attempts on failure
- Respectful User-Agent headers

## Legal Notes

- **ERIC**: Public government database, free API access
- **IRIS Center**: Federally funded (OSEP), explicitly provides free educational resources
- Both sources are intended for educational use

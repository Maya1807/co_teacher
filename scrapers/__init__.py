"""
Scrapers package for fetching educational content from external sources.

Sources:
- IRIS Center (Vanderbilt): Teaching modules and strategies
- ERIC API: Education research abstracts
"""

from scrapers.iris_scraper import IRISScraper
from scrapers.eric_fetcher import ERICFetcher

__all__ = ["IRISScraper", "ERICFetcher"]
